package br.com.inventario

import android.content.Context
import android.content.SharedPreferences
import br.com.inventario.util.SessionManager
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import io.mockk.spyk
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Testes da lógica de negócio do SessionManager.
 *
 * Usamos MockK para simular Context e SharedPreferences sem precisar
 * de emulador Android. Só testamos o comportamento — não a gravação em disco.
 */
class SessionManagerTest {

    // Mocks — objetos falsos que simulam o Android
    private lateinit var mockContext: Context
    private lateinit var mockPrefs: SharedPreferences
    private lateinit var mockEditor: SharedPreferences.Editor
    private lateinit var session: SessionManager

    @Before
    fun setup() {
        mockContext = mockk()
        mockPrefs   = mockk(relaxed = true)
        mockEditor  = mockk(relaxed = true)

        // Toda vez que alguém pedir SharedPreferences, devolve o mock
        every { mockContext.getSharedPreferences(any(), any()) } returns mockPrefs
        // Toda vez que alguém chamar prefs.edit(), devolve o editor mock
        every { mockPrefs.edit() } returns mockEditor

        session = SessionManager(mockContext)
    }

    // ─── isMI ────────────────────────────────────────────────────────────────

    @Test
    fun `isMI retorna true para usuario MI maiusculo`() {
        every { mockPrefs.getString("usuario", null) } returns "MI"
        assertTrue(session.isMI())
    }

    @Test
    fun `isMI retorna true para usuario mi minusculo`() {
        // isMI() faz uppercase() antes de comparar
        every { mockPrefs.getString("usuario", null) } returns "mi"
        assertTrue(session.isMI())
    }

    @Test
    fun `isMI retorna false para outros usuarios`() {
        every { mockPrefs.getString("usuario", null) } returns "VIVIANE"
        assertFalse(session.isMI())
    }

    // ─── isSupervisor ────────────────────────────────────────────────────────

    @Test
    fun `isSupervisor retorna true para MI`() {
        val s = spyk(session)
        every { s.getUsuario() } returns "MI"
        every { s.getRole() }    returns "operador"
        assertTrue(s.isSupervisor())
    }

    @Test
    fun `isSupervisor retorna true para role admin`() {
        val s = spyk(session)
        every { s.getUsuario() } returns "FULANO"
        every { s.getRole() }    returns "admin"
        assertTrue(s.isSupervisor())
    }

    @Test
    fun `isSupervisor retorna true para role gerente`() {
        val s = spyk(session)
        every { s.getUsuario() } returns "FULANO"
        every { s.getRole() }    returns "gerente"
        assertTrue(s.isSupervisor())
    }

    @Test
    fun `isSupervisor retorna false para operador comum`() {
        val s = spyk(session)
        every { s.getUsuario() } returns "CARLOS"
        every { s.getRole() }    returns "operador"
        assertFalse(s.isSupervisor())
    }

    // ─── canManageUsers ───────────────────────────────────────────────────────

    @Test
    fun `canManageUsers retorna true quando mobileAdmin e 1`() {
        every { mockPrefs.getInt("mobile_admin", 0) } returns 1
        assertTrue(session.canManageUsers())
    }

    @Test
    fun `canManageUsers retorna false quando mobileAdmin e 0`() {
        every { mockPrefs.getInt("mobile_admin", 0) } returns 0
        assertFalse(session.canManageUsers())
    }

    // ─── isLoggedIn ───────────────────────────────────────────────────────────

    @Test
    fun `isLoggedIn retorna true quando ha token`() {
        every { mockPrefs.getString("token", null) } returns "eyJhbGciOiJIUzI1NiJ9.payload.sig"
        assertTrue(session.isLoggedIn())
    }

    @Test
    fun `isLoggedIn retorna false sem token`() {
        every { mockPrefs.getString("token", null) } returns null
        assertFalse(session.isLoggedIn())
    }

    // ─── getConsiderarEntrega ─────────────────────────────────────────────────

    @Test
    fun `getConsiderarEntrega retorna false por padrao`() {
        every { mockPrefs.getBoolean("considerar_entrega", false) } returns false
        assertFalse(session.getConsiderarEntrega())
    }

    @Test
    fun `getConsiderarEntrega retorna true quando salvo como true`() {
        every { mockPrefs.getBoolean("considerar_entrega", false) } returns true
        assertTrue(session.getConsiderarEntrega())
    }

    // ─── logout preserva preferências ────────────────────────────────────────

    @Test
    fun `logout preserva server_url scan_mode e dark_mode`() {
        every { mockPrefs.getString("server_url",      any()) } returns "http://192.168.1.1:8000/"
        every { mockPrefs.getString("scan_mode",       any()) } returns "BLUETOOTH"
        every { mockPrefs.getBoolean("dark_mode",      any()) } returns true
        every { mockPrefs.getString("depositos_cache", null)  } returns null

        session.logout()

        // Verifica que os valores foram re-gravados no editor após o clear
        verify { mockEditor.putString("server_url", "http://192.168.1.1:8000/") }
        verify { mockEditor.putString("scan_mode",  "BLUETOOTH") }
        verify { mockEditor.putBoolean("dark_mode", true) }
    }

    @Test
    fun `logout nao preserva token nem usuario`() {
        every { mockPrefs.getString(any(),    any()) } returns "qualquer"
        every { mockPrefs.getBoolean(any(),   any()) } returns false
        every { mockPrefs.getString("depositos_cache", null) } returns null

        session.logout()

        // token e usuario NÃO devem ser re-gravados após o clear
        verify(exactly = 0) { mockEditor.putString("token",   any()) }
        verify(exactly = 0) { mockEditor.putString("usuario", any()) }
    }

    // ─── getCachedDepositos ───────────────────────────────────────────────────

    @Test
    fun `getCachedDepositos parseia JSON corretamente`() {
        val json = """[{"cddeposito":1,"deposito":"Matriz"},{"cddeposito":2,"deposito":"Filial"}]"""
        every { mockPrefs.getString("depositos_cache", null) } returns json

        val depositos = session.getCachedDepositos()

        assertNotNull(depositos)
        assertEquals(2, depositos!!.size)
        assertEquals(1,        depositos[0].cddeposito)
        assertEquals("Matriz", depositos[0].deposito)
        assertEquals(2,        depositos[1].cddeposito)
        assertEquals("Filial", depositos[1].deposito)
    }

    @Test
    fun `getCachedDepositos retorna null quando nao ha cache`() {
        every { mockPrefs.getString("depositos_cache", null) } returns null
        assertNull(session.getCachedDepositos())
    }

    @Test
    fun `getCachedDepositos retorna null para JSON invalido`() {
        every { mockPrefs.getString("depositos_cache", null) } returns "isso nao e json"
        assertNull(session.getCachedDepositos())
    }
}
