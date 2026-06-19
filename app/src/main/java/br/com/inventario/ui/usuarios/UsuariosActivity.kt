package br.com.inventario.ui.usuarios

import android.graphics.Color
import android.os.Bundle
import android.view.*
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import br.com.inventario.data.api.RetrofitClient
import br.com.inventario.data.model.SenhaMobileRequest
import br.com.inventario.data.model.UsuarioMobile
import br.com.inventario.databinding.ActivityUsuariosBinding
import br.com.inventario.databinding.ItemUsuarioBinding
import br.com.inventario.ui.base.TimeoutActivity
import br.com.inventario.util.SessionManager
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.launch

class UsuariosActivity : TimeoutActivity() {

    private lateinit var binding: ActivityUsuariosBinding
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityUsuariosBinding.inflate(layoutInflater)
        setContentView(binding.root)

        session = SessionManager(this)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = "Acesso Mobile — Usuários"
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        binding.recycler.layoutManager = LinearLayoutManager(this)
        carregar()
    }

    private fun carregar() {
        binding.progressBar.visibility = View.VISIBLE
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.listarUsuariosMobile()
                if (resp.isSuccessful) {
                    binding.recycler.adapter = Adapter(resp.body() ?: emptyList())
                } else {
                    Toast.makeText(this@UsuariosActivity, "Erro ao carregar usuários", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
            } catch (e: Exception) {
                Toast.makeText(this@UsuariosActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
            }
        }
    }

    private fun pedirSenha(usuario: UsuarioMobile) {
        val temAcesso = usuario.temMobile == 1
        val input = EditText(this).apply {
            hint = "Nova senha mobile (vazio = revogar acesso)"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or
                    android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        AlertDialog.Builder(this)
            .setTitle("${usuario.login} — ${if (temAcesso) "Alterar ou revogar acesso" else "Ativar acesso mobile"}")
            .setView(input)
            .setPositiveButton("Salvar") { _, _ ->
                salvarSenha(usuario.idusuario, input.text.toString().trim().ifBlank { null })
            }
            .setNegativeButton("Cancelar", null)
            .also { dlg ->
                if (temAcesso) {
                    dlg.setNeutralButton("Revogar acesso") { _, _ -> salvarSenha(usuario.idusuario, null) }
                }
            }
            .show()
    }

    private fun salvarSenha(idusuario: Int, senha: String?) {
        lifecycleScope.launch {
            try {
                val api = RetrofitClient.build(session)
                val resp = api.definirSenhaMobile(idusuario, SenhaMobileRequest(senha))
                if (resp.isSuccessful) {
                    Toast.makeText(
                        this@UsuariosActivity,
                        if (senha != null) "Acesso mobile ativado" else "Acesso mobile revogado",
                        Toast.LENGTH_SHORT
                    ).show()
                    carregar()
                } else {
                    Toast.makeText(this@UsuariosActivity, "Erro ao salvar", Toast.LENGTH_SHORT).show()
                }
            } catch (_: CancellationException) {
            } catch (e: Exception) {
                Toast.makeText(this@UsuariosActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun toggleAdmin(usuario: UsuarioMobile) {
        val acao = if (usuario.mobileAdmin == 1) "Remover acesso admin de" else "Dar acesso admin para"
        AlertDialog.Builder(this)
            .setTitle("$acao ${usuario.login}?")
            .setMessage(
                if (usuario.mobileAdmin == 1)
                    "${usuario.login} não poderá mais gerenciar usuários mobile."
                else
                    "${usuario.login} poderá ativar senhas e gerenciar usuários mobile, mas não poderá alterar o usuário MI."
            )
            .setPositiveButton("Confirmar") { _, _ ->
                lifecycleScope.launch {
                    try {
                        val api = RetrofitClient.build(session)
                        val resp = api.toggleAdminMobile(usuario.idusuario)
                        if (resp.isSuccessful) {
                            carregar()
                        } else {
                            Toast.makeText(this@UsuariosActivity, "Erro ao alterar permissão", Toast.LENGTH_SHORT).show()
                        }
                    } catch (_: CancellationException) {
                    } catch (e: Exception) {
                        Toast.makeText(this@UsuariosActivity, "Erro: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    override fun onSupportNavigateUp(): Boolean { finish(); return true }

    inner class Adapter(private val lista: List<UsuarioMobile>) :
        RecyclerView.Adapter<Adapter.VH>() {

        inner class VH(val b: ItemUsuarioBinding) : RecyclerView.ViewHolder(b.root)

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
            VH(ItemUsuarioBinding.inflate(LayoutInflater.from(parent.context), parent, false))

        override fun getItemCount() = lista.size

        override fun onBindViewHolder(holder: VH, position: Int) {
            val u = lista[position]
            val esMI = u.login.uppercase() == "MI"
            val euSouMI = session.isMI()

            with(holder.b) {
                tvLogin.text = u.login

                val (roleLabel, roleColor) = when (u.idgrupo) {
                    1 -> "ADMIN" to Color.parseColor("#1B5E20")
                    2 -> "GERENTE" to Color.parseColor("#E65100")
                    else -> "OPERADOR" to Color.parseColor("#37474F")
                }
                tvRole.text = roleLabel
                tvRole.background.setTint(roleColor)

                if (u.mobileAdmin == 1 && !esMI) {
                    tvAdminBadge.visibility = View.VISIBLE
                    tvAdminBadge.background.setTint(Color.parseColor("#6A1B9A"))
                } else {
                    tvAdminBadge.visibility = View.GONE
                }

                val nomeExibido = u.nomecompleto?.takeIf { it.isNotBlank() && !it.all { c -> c.isDigit() } }
                tvNome.text = nomeExibido ?: ""
                tvNome.visibility = if (nomeExibido != null) View.VISIBLE else View.GONE

                if (esMI && !euSouMI) {
                    btnSenha.visibility = View.GONE
                    btnToggleAdmin.visibility = View.GONE
                } else if (esMI) {
                    btnSenha.visibility = View.VISIBLE
                    btnSenha.text = if (u.temMobile == 1) "Alterar senha" else "Ativar acesso"
                    btnSenha.setOnClickListener { pedirSenha(u) }
                    btnToggleAdmin.visibility = View.GONE
                } else {
                    btnSenha.visibility = View.VISIBLE
                    btnSenha.text = if (u.temMobile == 1) "Alterar senha" else "Ativar acesso"
                    btnSenha.setOnClickListener { pedirSenha(u) }

                    if (euSouMI) {
                        btnToggleAdmin.visibility = View.VISIBLE
                        btnToggleAdmin.text = if (u.mobileAdmin == 1) "Remover acesso admin" else "Dar acesso admin"
                        btnToggleAdmin.setOnClickListener { toggleAdmin(u) }
                    } else {
                        btnToggleAdmin.visibility = View.GONE
                    }
                }
            }
        }
    }
}
