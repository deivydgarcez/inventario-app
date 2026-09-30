package br.com.inventario.ui.splash

import android.content.Intent
import android.os.Bundle
import android.view.animation.DecelerateInterpolator
import androidx.appcompat.app.AppCompatActivity
import br.com.inventario.databinding.ActivitySplashBinding
import br.com.inventario.ui.login.LoginActivity

class SplashActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySplashBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySplashBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.ivSplashLogo.animate()
            .alpha(1f)
            .translationY(-24f)
            .setDuration(700)
            .setInterpolator(DecelerateInterpolator())
            .start()

        binding.tvSplashTagline.animate()
            .alpha(1f)
            .setStartDelay(350)
            .setDuration(600)
            .setInterpolator(DecelerateInterpolator())
            .start()

        binding.root.postDelayed({
            val intent = Intent(this, LoginActivity::class.java)
            val options = android.app.ActivityOptions.makeCustomAnimation(
                this, android.R.anim.fade_in, android.R.anim.fade_out
            )
            startActivity(intent, options.toBundle())
            finish()
        }, 1700)
    }
}
