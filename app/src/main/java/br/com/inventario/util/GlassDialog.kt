package br.com.inventario.util

import android.content.Context
import android.content.res.ColorStateList
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.text.InputType
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.core.content.ContextCompat
import androidx.core.widget.NestedScrollView
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import br.com.inventario.R

object GlassDialog {

    private fun makeDialog(context: Context, view: View): AlertDialog {
        val d = AlertDialog.Builder(context).setView(view).create()
        d.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
        return d
    }

    private fun showDialog(context: Context, dialog: AlertDialog) {
        dialog.show()
        dialog.window?.setLayout(
            (context.resources.displayMetrics.widthPixels * 0.88).toInt(),
            ViewGroup.LayoutParams.WRAP_CONTENT
        )
    }

    fun show(
        context: Context,
        title: String,
        message: String,
        positiveText: String = "OK",
        negativeText: String? = null,
        cancelable: Boolean = true,
        equalButtons: Boolean = false,
        onPositive: (() -> Unit)? = null,
        onNegative: (() -> Unit)? = null
    ) {
        val view = LayoutInflater.from(context).inflate(R.layout.dialog_glass_alert, null)
        view.findViewById<TextView>(R.id.dialogTitle).text = title
        view.findViewById<TextView>(R.id.dialogMessage).text = message

        val btnPositive = view.findViewById<MaterialButton>(R.id.dialogBtnPositive)
        val btnNegative = view.findViewById<MaterialButton>(R.id.dialogBtnNegative)

        btnPositive.text = positiveText
        if (negativeText != null) {
            btnNegative.text = negativeText
            btnNegative.visibility = View.VISIBLE
        }

        val dm = context.resources.displayMetrics
        val btnLayout = view.findViewById<LinearLayout>(R.id.dialogBtnLayout)

        if (equalButtons) {
            // Same glass style for both buttons — no color hierarchy for genuine choices
            val glassColor = ColorStateList.valueOf(Color.parseColor("#26FFFFFF"))
            val borderColor = ColorStateList.valueOf(ContextCompat.getColor(context, R.color.glassCardBorder))
            val textColor = ContextCompat.getColor(context, R.color.colorPrimaryText)
            btnPositive.backgroundTintList = glassColor
            btnPositive.strokeColor = borderColor
            btnPositive.setTextColor(textColor)

            // Stack buttons vertically so long labels fit on one line
            btnLayout.orientation = LinearLayout.VERTICAL
            listOf(btnNegative, btnPositive).forEach { btn ->
                (btn.layoutParams as LinearLayout.LayoutParams).apply {
                    width = ViewGroup.LayoutParams.MATCH_PARENT
                    weight = 0f
                    marginStart = 0
                    marginEnd = 0
                }
            }
            // Add spacing between stacked buttons
            (btnPositive.layoutParams as LinearLayout.LayoutParams).topMargin =
                (8 * dm.density).toInt()
        }

        // Cap scroll area height so dialog never overflows screen.
        // Use exact width for accurate line-wrap measurement, then compare against
        // a conservative 68% of raw screen pixels (leaves room for status/nav bars).
        val dialogW = (dm.widthPixels * 0.88).toInt()
        val maxH = (dm.heightPixels * 0.68).toInt()
        view.measure(
            View.MeasureSpec.makeMeasureSpec(dialogW, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
        )
        if (view.measuredHeight > maxH) {
            val scrollView = view.findViewById<NestedScrollView>(R.id.dialogMessageScroll)
            scrollView.measure(
                View.MeasureSpec.makeMeasureSpec(dialogW, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED)
            )
            val nonScroll = view.measuredHeight - scrollView.measuredHeight
            scrollView.layoutParams.height = maxOf(maxH - nonScroll, (60 * dm.density).toInt())
        }

        val dialog = makeDialog(context, view)
        dialog.setCancelable(cancelable)
        btnPositive.setOnClickListener { dialog.dismiss(); onPositive?.invoke() }
        btnNegative.setOnClickListener { dialog.dismiss(); onNegative?.invoke() }
        showDialog(context, dialog)
    }

    fun list(
        context: Context,
        title: String,
        items: Array<String>,
        negativeText: String? = null,
        onNegative: (() -> Unit)? = null,
        onSelect: (Int) -> Unit
    ) {
        val view = LayoutInflater.from(context).inflate(R.layout.dialog_glass_list, null)
        view.findViewById<TextView>(R.id.dialogListTitle).text = title
        val container = view.findViewById<LinearLayout>(R.id.dialogListContainer)

        val isDark = (context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
                Configuration.UI_MODE_NIGHT_YES
        val dividerColor = if (isDark) Color.parseColor("#33FFFFFF") else Color.parseColor("#22000000")
        val textColor = ContextCompat.getColor(context, R.color.colorPrimaryText)
        val density = context.resources.displayMetrics.density
        val hPad = (20 * density).toInt()
        val vPad = (15 * density).toInt()

        val dialog = makeDialog(context, view)

        items.forEachIndexed { index, item ->
            val tv = TextView(context).apply {
                text = item
                textSize = 14f
                setTextColor(textColor)
                setPadding(hPad, vPad, hPad, vPad)
                val ripple = android.util.TypedValue()
                context.theme.resolveAttribute(android.R.attr.selectableItemBackground, ripple, true)
                setBackgroundResource(ripple.resourceId)
                isClickable = true
                isFocusable = true
                setOnClickListener { dialog.dismiss(); onSelect(index) }
            }
            container.addView(tv)
            if (index < items.size - 1) {
                container.addView(View(context).apply {
                    layoutParams = LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT, 1
                    ).also { lp -> lp.marginStart = hPad; lp.marginEnd = hPad }
                    setBackgroundColor(dividerColor)
                })
            }
        }

        if (negativeText != null) {
            val btnRow = view.findViewById<LinearLayout>(R.id.dialogListBtnRow)
            val btnNeg = view.findViewById<MaterialButton>(R.id.dialogListBtnNegative)
            btnNeg.text = negativeText
            btnRow.visibility = View.VISIBLE
            btnNeg.setOnClickListener { dialog.dismiss(); onNegative?.invoke() }
        }

        showDialog(context, dialog)
    }

    fun showLoading(context: Context, titulo: String, mensagem: String): Pair<AlertDialog, TextView> {
        val view = LayoutInflater.from(context).inflate(R.layout.dialog_glass_alert, null)
        view.findViewById<TextView>(R.id.dialogTitle).text = titulo
        val tvMsg = view.findViewById<TextView>(R.id.dialogMessage)
        tvMsg.text = mensagem
        view.findViewById<LinearLayout>(R.id.dialogBtnLayout).visibility = View.GONE
        val dialog = makeDialog(context, view)
        dialog.setCancelable(false)
        showDialog(context, dialog)
        return Pair(dialog, tvMsg)
    }

    fun input(
        context: Context,
        title: String,
        hint: String,
        message: String? = null,
        prefilled: String = "",
        inputType: Int = InputType.TYPE_CLASS_TEXT,
        positiveText: String = "OK",
        negativeText: String = "Cancelar",
        onPositive: (String) -> Unit
    ) {
        val view = LayoutInflater.from(context).inflate(R.layout.dialog_glass_input, null)
        view.findViewById<TextView>(R.id.dialogInputTitle).text = title

        val tvMsg = view.findViewById<TextView>(R.id.dialogInputMessage)
        if (!message.isNullOrEmpty()) {
            tvMsg.text = message
            tvMsg.visibility = View.VISIBLE
        }

        view.findViewById<TextInputLayout>(R.id.dialogInputLayout).hint = hint
        val editText = view.findViewById<TextInputEditText>(R.id.dialogInputField)
        editText.inputType = inputType
        if (prefilled.isNotEmpty()) {
            editText.setText(prefilled)
            editText.setSelection(prefilled.length)
        }

        val btnPositive = view.findViewById<MaterialButton>(R.id.dialogInputBtnPositive)
        val btnNegative = view.findViewById<MaterialButton>(R.id.dialogInputBtnNegative)
        btnPositive.text = positiveText
        btnNegative.text = negativeText

        val dialog = makeDialog(context, view)
        btnPositive.setOnClickListener {
            dialog.dismiss()
            onPositive(editText.text.toString().trim())
        }
        btnNegative.setOnClickListener { dialog.dismiss() }

        showDialog(context, dialog)
        editText.requestFocus()
        dialog.window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE)
    }
}
