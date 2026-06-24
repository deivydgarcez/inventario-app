package br.com.inventario.data.db

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

// ── Entidades locais ──────────────────────────────────────────────────────────

data class BipagPendente(
    val id: Long = 0,
    val sessionId: String,
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtde: Double,
    val cddeposito: Int,
    val operador: String?,
    val deviceId: String?,
    val qtdeSistema: Double,
    val timestamp: Long = System.currentTimeMillis(),
    val sincronizado: Boolean = false,
    val scanId: String = "",
)

data class ProdutoCache(
    val codigobarra: String,
    val cddeposito: Int,
    val cdproduto: Int,
    val produto: String,
    val qtdeatual: Double,
    val syncedAt: Long = System.currentTimeMillis(),
)

data class ItemRelatorioLocal(
    val cdproduto: Int,
    val produto: String,
    val codigobarra: String?,
    val qtdeSistema: Double,
    val qtdeContada: Double,
    val diferenca: Double,
    val operador: String?,
)

// ── Banco de dados ────────────────────────────────────────────────────────────

class InvecDatabase private constructor(context: Context) :
    SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION) {

    companion object {
        private const val DB_NAME = "invec_offline.db"
        private const val DB_VERSION = 3

        @Volatile
        private var INSTANCE: InvecDatabase? = null

        fun getInstance(context: Context): InvecDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: InvecDatabase(context.applicationContext).also { INSTANCE = it }
            }
    }

    val bipag by lazy { BipagPendenteDao(this) }
    val catalogo by lazy { ProdutoCacheDao(this) }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE bipagens_pendentes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT    NOT NULL,
                cdproduto    INTEGER NOT NULL,
                produto      TEXT    NOT NULL,
                codigobarra  TEXT,
                qtde         REAL    NOT NULL,
                cddeposito   INTEGER NOT NULL,
                operador     TEXT,
                device_id    TEXT,
                qtde_sistema REAL    NOT NULL DEFAULT 0,
                timestamp    INTEGER NOT NULL,
                sincronizado INTEGER NOT NULL DEFAULT 0,
                scan_id      TEXT    NOT NULL DEFAULT ''
            )
            """
        )
        db.execSQL("CREATE INDEX idx_bp_session ON bipagens_pendentes(session_id, cddeposito)")
        db.execSQL("CREATE INDEX idx_bp_sync    ON bipagens_pendentes(sincronizado, cddeposito)")

        criarTabelaCatalogo(db)
    }

    private fun criarTabelaCatalogo(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE produtos_cache (
                codigobarra TEXT    NOT NULL,
                cddeposito  INTEGER NOT NULL,
                cdproduto   INTEGER NOT NULL,
                produto     TEXT    NOT NULL,
                qtdeatual   REAL    NOT NULL DEFAULT 0,
                synced_at   INTEGER NOT NULL,
                PRIMARY KEY (codigobarra, cddeposito)
            )
            """
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            db.execSQL("DROP TABLE IF EXISTS produtos_cache")
            criarTabelaCatalogo(db)
        }
        if (oldVersion < 3) {
            db.execSQL("ALTER TABLE bipagens_pendentes ADD COLUMN scan_id TEXT NOT NULL DEFAULT ''")
        }
    }
}

// ── DAO: bipagens pendentes ───────────────────────────────────────────────────

class BipagPendenteDao(private val helper: InvecDatabase) {

    fun insert(item: BipagPendente): Long {
        val cv = ContentValues().apply {
            put("session_id",   item.sessionId)
            put("cdproduto",    item.cdproduto)
            put("produto",      item.produto)
            put("codigobarra",  item.codigobarra)
            put("qtde",         item.qtde)
            put("cddeposito",   item.cddeposito)
            put("operador",     item.operador)
            put("device_id",    item.deviceId)
            put("qtde_sistema", item.qtdeSistema)
            put("timestamp",    item.timestamp)
            put("sincronizado", 0)
            put("scan_id",      item.scanId)
        }
        return helper.writableDatabase.insert("bipagens_pendentes", null, cv)
    }

    /** Snapshot de estoque no momento do 1º scan deste produto nesta sessão. */
    fun getQtdeSistema(cdproduto: Int, sessionId: String): Double? =
        helper.readableDatabase.rawQuery(
            "SELECT qtde_sistema FROM bipagens_pendentes WHERE cdproduto=? AND session_id=? ORDER BY timestamp ASC LIMIT 1",
            arrayOf(cdproduto.toString(), sessionId)
        ).useFirst { it.getDouble(0) }

    fun getQtdeAcumulada(cdproduto: Int, sessionId: String): Double =
        helper.readableDatabase.rawQuery(
            "SELECT COALESCE(SUM(qtde),0) FROM bipagens_pendentes WHERE cdproduto=? AND session_id=?",
            arrayOf(cdproduto.toString(), sessionId)
        ).useFirst { it.getDouble(0) } ?: 0.0

    fun countPendentes(sessionId: String): Int =
        helper.readableDatabase.rawQuery(
            "SELECT COUNT(*) FROM bipagens_pendentes WHERE session_id=? AND sincronizado=0",
            arrayOf(sessionId)
        ).useFirst { it.getInt(0) } ?: 0

    fun getNaoSincronizados(cddeposito: Int): List<BipagPendente> =
        helper.readableDatabase.rawQuery(
            "SELECT * FROM bipagens_pendentes WHERE cddeposito=? AND sincronizado=0 ORDER BY timestamp ASC",
            arrayOf(cddeposito.toString())
        ).useAll { it.toBipag() }

    fun marcarSincronizados(ids: List<Long>) {
        if (ids.isEmpty()) return
        val placeholders = ids.joinToString(",") { "?" }
        helper.writableDatabase.execSQL(
            "UPDATE bipagens_pendentes SET sincronizado=1 WHERE id IN ($placeholders)",
            ids.map { it.toString() }.toTypedArray()
        )
    }

    fun marcarSincronizado(id: Long) = marcarSincronizados(listOf(id))

    fun deleteAllDaSessao(sessionId: String) {
        helper.writableDatabase.delete("bipagens_pendentes", "session_id=?", arrayOf(sessionId))
    }

    fun atualizarQtdeProduto(cdproduto: Int, sessionId: String, novaQtde: Double, offline: Boolean = false) {
        // Offline: precisa calcular o delta = novaQtde - já_sincronizado para não dobrar no lote.
        // Online: o servidor já recebeu a edição diretamente; apenas consolida o Room.
        val syncedSum: Double = if (offline) {
            helper.readableDatabase.rawQuery(
                "SELECT COALESCE(SUM(qtde),0) FROM bipagens_pendentes WHERE cdproduto=? AND session_id=? AND sincronizado=1",
                arrayOf(cdproduto.toString(), sessionId)
            ).useFirst { it.getDouble(0) } ?: 0.0
        } else 0.0

        val qtdeParaArmazenar = if (offline) novaQtde - syncedSum else novaQtde

        val cv = helper.readableDatabase.rawQuery(
            "SELECT produto, codigobarra, cddeposito, operador, device_id, qtde_sistema " +
            "FROM bipagens_pendentes WHERE cdproduto=? AND session_id=? ORDER BY timestamp ASC LIMIT 1",
            arrayOf(cdproduto.toString(), sessionId)
        ).useFirst { c ->
            ContentValues().apply {
                put("session_id",   sessionId)
                put("cdproduto",    cdproduto)
                put("produto",      c.getString(0) ?: "")
                val barcode = c.getString(1); if (barcode != null) put("codigobarra", barcode) else putNull("codigobarra")
                put("qtde",         qtdeParaArmazenar)
                put("cddeposito",   c.getInt(2))
                val op = c.getString(3); if (op != null) put("operador", op) else putNull("operador")
                val did = c.getString(4); if (did != null) put("device_id", did) else putNull("device_id")
                put("qtde_sistema", c.getDouble(5))
                put("timestamp",    System.currentTimeMillis())
                put("sincronizado", if (offline) 0 else 1)
                put("scan_id",      "")
            }
        } ?: return

        val db = helper.writableDatabase
        db.beginTransaction()
        try {
            if (offline) {
                // Mantém registros já sincronizados (referência do que o servidor tem).
                // Remove apenas os pendentes e insere o delta para o próximo lote.
                db.delete("bipagens_pendentes", "cdproduto=? AND session_id=? AND sincronizado=0",
                    arrayOf(cdproduto.toString(), sessionId))
                if (qtdeParaArmazenar != 0.0) {
                    db.insert("bipagens_pendentes", null, cv)
                }
            } else {
                // Online: servidor já foi atualizado; consolida Room com valor final marcado como synced.
                db.delete("bipagens_pendentes", "cdproduto=? AND session_id=?",
                    arrayOf(cdproduto.toString(), sessionId))
                db.insert("bipagens_pendentes", null, cv)
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    fun getRelatorioOffline(sessionId: String, cddeposito: Int): List<ItemRelatorioLocal> =
        helper.readableDatabase.rawQuery(
            """
            SELECT cdproduto, produto,
                   MAX(codigobarra) AS codigobarra,
                   (SELECT qtde_sistema FROM bipagens_pendentes b2
                    WHERE b2.cdproduto=b.cdproduto AND b2.session_id=b.session_id
                    ORDER BY timestamp ASC LIMIT 1) AS qtde_sistema,
                   SUM(qtde)  AS qtde_contada,
                   MAX(operador) AS operador
            FROM bipagens_pendentes b
            WHERE session_id=? AND cddeposito=?
            GROUP BY cdproduto
            ORDER BY MAX(produto)
            """,
            arrayOf(sessionId, cddeposito.toString())
        ).useAll { c ->
            val qtdeSistema = c.getDouble(c.getColumnIndexOrThrow("qtde_sistema"))
            val qtdeContada = c.getDouble(c.getColumnIndexOrThrow("qtde_contada"))
            ItemRelatorioLocal(
                cdproduto   = c.getInt(c.getColumnIndexOrThrow("cdproduto")),
                produto     = c.getString(c.getColumnIndexOrThrow("produto")),
                codigobarra = c.getString(c.getColumnIndexOrThrow("codigobarra")),
                qtdeSistema = qtdeSistema,
                qtdeContada = qtdeContada,
                diferenca   = qtdeContada - qtdeSistema,
                operador    = c.getString(c.getColumnIndexOrThrow("operador")),
            )
        }

    private fun Cursor.toBipag() = BipagPendente(
        id           = getLong(getColumnIndexOrThrow("id")),
        sessionId    = getString(getColumnIndexOrThrow("session_id")),
        cdproduto    = getInt(getColumnIndexOrThrow("cdproduto")),
        produto      = getString(getColumnIndexOrThrow("produto")),
        codigobarra  = getString(getColumnIndexOrThrow("codigobarra")),
        qtde         = getDouble(getColumnIndexOrThrow("qtde")),
        cddeposito   = getInt(getColumnIndexOrThrow("cddeposito")),
        operador     = getString(getColumnIndexOrThrow("operador")),
        deviceId     = getString(getColumnIndexOrThrow("device_id")),
        qtdeSistema  = getDouble(getColumnIndexOrThrow("qtde_sistema")),
        timestamp    = getLong(getColumnIndexOrThrow("timestamp")),
        sincronizado = getInt(getColumnIndexOrThrow("sincronizado")) == 1,
        scanId       = getString(getColumnIndexOrThrow("scan_id")) ?: "",
    )
}

// ── DAO: catálogo de produtos ─────────────────────────────────────────────────

class ProdutoCacheDao(private val helper: InvecDatabase) {

    fun upsertBatch(items: List<ProdutoCache>) {
        if (items.isEmpty()) return
        val db = helper.writableDatabase
        db.beginTransaction()
        try {
            val stmt = db.compileStatement(
                "INSERT OR REPLACE INTO produtos_cache (codigobarra,cddeposito,cdproduto,produto,qtdeatual,synced_at) VALUES (?,?,?,?,?,?)"
            )
            for (item in items) {
                stmt.bindString(1, item.codigobarra)
                stmt.bindLong(2, item.cddeposito.toLong())
                stmt.bindLong(3, item.cdproduto.toLong())
                stmt.bindString(4, item.produto)
                stmt.bindDouble(5, item.qtdeatual)
                stmt.bindLong(6, item.syncedAt)
                stmt.executeInsert()
                stmt.clearBindings()
            }
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
    }

    fun getByBarcode(barcode: String, cddeposito: Int): ProdutoCache? =
        helper.readableDatabase.rawQuery(
            "SELECT * FROM produtos_cache WHERE codigobarra=? AND cddeposito=? LIMIT 1",
            arrayOf(barcode, cddeposito.toString())
        ).useFirst { it.toCache() }

    fun count(cddeposito: Int): Int =
        helper.readableDatabase.rawQuery(
            "SELECT COUNT(*) FROM produtos_cache WHERE cddeposito=?",
            arrayOf(cddeposito.toString())
        ).useFirst { it.getInt(0) } ?: 0

    /** BUG-6: retorna barcode→cdproduto para todos os produtos da lista (inclui secundários). */
    fun getAllBarcodesForCdprodutos(cdprodutos: List<Int>, cddeposito: Int): Map<String, Int> {
        if (cdprodutos.isEmpty()) return emptyMap()
        val placeholders = cdprodutos.joinToString(",") { "?" }
        val result = mutableMapOf<String, Int>()
        helper.readableDatabase.rawQuery(
            "SELECT codigobarra, cdproduto FROM produtos_cache " +
            "WHERE cdproduto IN ($placeholders) AND cddeposito=? " +
            "AND codigobarra IS NOT NULL AND codigobarra != ''",
            (cdprodutos.map { it.toString() } + listOf(cddeposito.toString())).toTypedArray()
        ).useAll { c -> result[c.getString(0)] = c.getInt(1) }
        return result
    }

    private fun Cursor.toCache() = ProdutoCache(
        codigobarra = getString(getColumnIndexOrThrow("codigobarra")),
        cddeposito  = getInt(getColumnIndexOrThrow("cddeposito")),
        cdproduto   = getInt(getColumnIndexOrThrow("cdproduto")),
        produto     = getString(getColumnIndexOrThrow("produto")),
        qtdeatual   = getDouble(getColumnIndexOrThrow("qtdeatual")),
        syncedAt    = getLong(getColumnIndexOrThrow("synced_at")),
    )
}

// ── Extensões de cursor ───────────────────────────────────────────────────────

private inline fun <T> Cursor.useFirst(block: (Cursor) -> T): T? =
    use { if (moveToFirst()) block(this) else null }

private inline fun <T> Cursor.useAll(block: (Cursor) -> T): List<T> =
    use { c ->
        val list = mutableListOf<T>()
        while (c.moveToNext()) list.add(block(c))
        list
    }
