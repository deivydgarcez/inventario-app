plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "br.com.inventario"
    compileSdk = 37

    defaultConfig {
        applicationId = "br.com.inventario"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        // Altere para o IP do servidor onde o backend FastAPI está rodando.
        // Use 10.0.2.2 para emulador Android (aponta para localhost da máquina).
        buildConfigField("String", "API_BASE_URL", "\"http://192.168.0.31:8000/\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true       // obfuscação e remoção de código morto
            isShrinkResources = true     // remove recursos não usados (imagens, strings)
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.lifecycle.viewmodel)
    implementation(libs.lifecycle.runtime)
    implementation(libs.retrofit)
    implementation(libs.retrofit.gson)
    implementation(libs.okhttp.logging)
    implementation(libs.gson)
    implementation(libs.coroutines.android)
    implementation(libs.camerax.core)
    implementation(libs.camerax.camera2)
    implementation(libs.camerax.lifecycle)
    implementation(libs.camerax.view)
    implementation(libs.mlkit.barcode)

    testImplementation("junit:junit:4.13.2")
    testImplementation("io.mockk:mockk:1.13.12")
    testImplementation("org.json:json:20231013")
}
