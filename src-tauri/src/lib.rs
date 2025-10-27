use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;

// State to track the Python backend process
struct PythonBackend {
    process: Mutex<Option<std::process::Child>>,
}

/// Kill any process using the specified port
/// This handles orphaned processes from previous crashes
fn kill_process_on_port(port: u16) -> Result<(), String> {
    println!("Checking for processes on port {}...", port);

    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        // Use lsof to find processes using the port
        let output = Command::new("lsof")
            .args(&["-ti", &format!(":{}", port)])
            .output()
            .map_err(|e| format!("Failed to check port (lsof not available?): {}", e))?;

        if output.status.success() && !output.stdout.is_empty() {
            let pid_str = String::from_utf8_lossy(&output.stdout);
            let pids: Vec<&str> = pid_str.trim().split('\n').collect();

            for pid in pids {
                if !pid.trim().is_empty() {
                    println!("Killing process on port {}: PID {}", port, pid.trim());
                    let _ = Command::new("kill")
                        .args(&["-9", pid.trim()])
                        .output();
                }
            }
            // Give processes time to die
            std::thread::sleep(Duration::from_millis(500));
        } else {
            println!("Port {} is free", port);
        }
    }

    #[cfg(target_os = "windows")]
    {
        // Use netstat to find processes using the port
        let output = Command::new("netstat")
            .args(&["-ano"])
            .output()
            .map_err(|e| format!("Failed to check port: {}", e))?;

        if output.status.success() {
            let output_str = String::from_utf8_lossy(&output.stdout);
            let mut killed_pids = std::collections::HashSet::new();

            for line in output_str.lines() {
                if line.contains(&format!(":{}", port)) && line.contains("LISTENING") {
                    if let Some(pid) = line.split_whitespace().last() {
                        if !killed_pids.contains(pid) {
                            println!("Killing process on port {}: PID {}", port, pid);
                            let _ = Command::new("taskkill")
                                .args(&["/F", "/PID", pid])
                                .output();
                            killed_pids.insert(pid.to_string());
                        }
                    }
                }
            }
            if !killed_pids.is_empty() {
                std::thread::sleep(Duration::from_millis(500));
            } else {
                println!("Port {} is free", port);
            }
        }
    }

    Ok(())
}

/// Wait for backend to be ready by polling the health endpoint
async fn wait_for_backend_ready(max_retries: u32, delay_ms: u64) -> Result<(), String> {
    println!("Waiting for backend to be ready...");

    for attempt in 1..=max_retries {
        tokio::time::sleep(Duration::from_millis(delay_ms)).await;

        match reqwest::get("http://localhost:8000/health").await {
            Ok(response) if response.status().is_success() => {
                println!("✓ Backend is ready!");
                return Ok(());
            }
            Ok(response) => {
                println!("Backend responded with status: {} (attempt {}/{})",
                    response.status(), attempt, max_retries);
            }
            Err(e) => {
                if attempt < max_retries {
                    println!("Waiting for backend... (attempt {}/{}) - {}",
                        attempt, max_retries, e);
                }
            }
        }
    }

    Err("Backend failed to start within timeout period".to_string())
}

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
async fn start_python_backend(
    python_backend: tauri::State<'_, PythonBackend>,
) -> Result<String, String> {
    println!("Starting Python backend...");

    // Kill any orphaned processes on port 8000 first
    if let Err(e) = kill_process_on_port(8000) {
        eprintln!("Warning: Failed to clean up port 8000: {}", e);
    }

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
        .env("PORT", "8000")
        .env("TAURI_MANAGED", "true");  // Signal to disable reload

    // Kill any previously tracked process
    let existing_process = {
        let mut state_guard = python_backend
            .process
            .lock()
            .map_err(|e| format!("Failed to lock backend state: {}", e))?;
        state_guard.take()
    };

    if let Some(mut existing) = existing_process {
        if let Err(kill_err) = existing.kill() {
            eprintln!("Failed to kill existing backend process: {}", kill_err);
        }
        let _ = existing.wait();
    }

    match command.spawn() {
        Ok(process) => {
            let pid = process.id();
            {
                let mut state_guard = python_backend
                    .process
                    .lock()
                    .map_err(|e| format!("Failed to lock backend state: {}", e))?;
                *state_guard = Some(process);
            }

            println!("Python backend started with PID: {}", pid);

            // Wait for backend to be ready (30 retries * 500ms = 15 seconds max)
            wait_for_backend_ready(30, 500).await?;

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
                let backend_state = app_handle.state::<PythonBackend>();
                match start_python_backend(backend_state).await {
                    Ok(msg) => println!("✓ {}", msg),
                    Err(err) => eprintln!("✗ Failed to start backend: {}", err),
                }
            });

            // Add graceful shutdown on window close
            let backend_handle = app.handle().clone();
            if let Some(window) = app.get_webview_window("main") {
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { .. } = event {
                        println!("Window closing, cleaning up backend...");
                        let backend_state = backend_handle.state::<PythonBackend>();
                        if let Ok(mut guard) = backend_state.process.lock() {
                            if let Some(mut process) = guard.take() {
                                if let Err(e) = process.kill() {
                                    eprintln!("Failed to kill backend process: {}", e);
                                } else {
                                    println!("Backend process terminated gracefully");
                                }
                                let _ = process.wait();
                            }
                        };
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
