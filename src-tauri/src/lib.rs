use tauri::Manager;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

// State to track the Python backend process
struct PythonBackend {
    process: Mutex<Option<std::process::Child>>,
}

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn start_python_backend() -> Result<String, String> {
    println!("Starting Python backend...");

    // Get the app directory - need to go up one level from src-tauri in dev mode
    let current_dir = std::env::current_dir()
        .map_err(|e| format!("Failed to get current directory: {}", e))?;

    // Try current directory first, then parent directory (for dev mode)
    let python_backend_dir = if current_dir.join("python-backend").exists() {
        current_dir.join("python-backend")
    } else {
        current_dir.parent()
            .ok_or("Cannot find parent directory")?
            .join("python-backend")
    };

    // Check if the Python backend directory exists
    println!("Looking for python-backend at: {:?}", python_backend_dir);
    if !python_backend_dir.exists() {
        return Err(format!("Python backend directory not found at: {:?}", python_backend_dir));
    }

    // Find the Python executable (prefer virtual environment)
    let python_exe = if current_dir.join(".venv/bin/python").exists() {
        current_dir.join(".venv/bin/python")
    } else if current_dir.parent().map(|p| p.join(".venv/bin/python").exists()).unwrap_or(false) {
        current_dir.parent().unwrap().join(".venv/bin/python")
    } else {
        std::path::PathBuf::from("python3")
    };

    // Start the Python FastAPI server
    println!("Using Python executable: {:?}", python_exe);
    println!("Starting server in directory: {:?}", python_backend_dir);

    let mut command = Command::new(&python_exe);
    command
        .arg("main.py")
        .current_dir(&python_backend_dir)
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .env("PORT", "8000");

    match command.spawn() {
        Ok(process) => {
            println!("Python backend started with PID: {}", process.id());

            // Give the server a moment to start
            thread::sleep(Duration::from_secs(2));

            Ok("Python backend started successfully".to_string())
        }
        Err(e) => {
            Err(format!("Failed to start Python backend: {}", e))
        }
    }
}

#[tauri::command]
async fn check_backend_health() -> Result<bool, String> {
    // Check if the backend is responding
    match reqwest::get("http://localhost:8000/health").await {
        Ok(response) => Ok(response.status().is_success()),
        Err(_) => Ok(false),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(PythonBackend {
            process: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            greet,
            start_python_backend,
            check_backend_health
        ])
        .setup(|app| {
            // Start Python backend on app startup
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                match start_python_backend().await {
                    Ok(msg) => println!("✓ {}", msg),
                    Err(err) => eprintln!("✗ Failed to start backend: {}", err),
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
