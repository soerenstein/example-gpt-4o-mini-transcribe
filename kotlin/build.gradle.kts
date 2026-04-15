plugins {
    kotlin("jvm") version "2.1.21"
    application
}

import org.jetbrains.kotlin.gradle.dsl.JvmTarget

repositories {
    mavenCentral()
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

dependencies {
    implementation("io.github.cdimascio:java-dotenv:5.2.2")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

application {
    mainClass.set("TranscribeFileKt")
}

tasks.named<JavaExec>("run") {
    if (project.hasProperty("audioFile")) {
        args(project.property("audioFile").toString())
    }
}
