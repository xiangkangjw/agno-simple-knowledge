"""Native macOS application using PyQt6 for the knowledge management system."""

import sys
import os
import logging
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QFileDialog,
    QMessageBox, QSplitter, QTabWidget, QListWidget, QListWidgetItem,
    QProgressBar, QStatusBar, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction

# Ensure repository root is on sys.path for package imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.chat_agent import KnowledgeAgent
from src.config import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndexingThread(QThread):
    """Background thread for document indexing operations."""
    
    progress = pyqtSignal(str)  # Progress message
    finished = pyqtSignal(bool, str)  # Success status and message
    
    def __init__(self, agent: KnowledgeAgent, operation: str, file_paths: Optional[List[str]] = None):
        super().__init__()
        self.agent = agent
        self.operation = operation
        self.file_paths = file_paths or []
        
    def run(self):
        """Execute the indexing operation in the background."""
        try:
            if self.operation == "refresh":
                self.progress.emit("Refreshing document index...")
                success = self.agent.query_engine.refresh_index()
                if success:
                    stats = self.agent.query_engine.get_index_stats()
                    message = f"Index refreshed! Now indexing {stats.get('document_count', 0)} documents."
                    self.finished.emit(True, message)
                else:
                    self.finished.emit(False, "Failed to refresh index.")
                    
            elif self.operation == "add_documents":
                self.progress.emit(f"Adding {len(self.file_paths)} documents...")
                success = self.agent.query_engine.add_documents(self.file_paths)
                if success:
                    message = f"Successfully added {len(self.file_paths)} documents."
                    self.finished.emit(True, message)
                else:
                    self.finished.emit(False, "Failed to add documents.")
                    
        except Exception as e:
            logger.error(f"Indexing operation failed: {e}")
            self.finished.emit(False, f"Error: {str(e)}")

class ChatThread(QThread):
    """Background thread for chat processing."""
    
    response_ready = pyqtSignal(str)  # Chat response
    error = pyqtSignal(str)  # Error message
    
    def __init__(self, agent: KnowledgeAgent, message: str):
        super().__init__()
        self.agent = agent
        self.message = message
        
    def run(self):
        """Process the chat message in the background."""
        try:
            response = self.agent.chat(self.message)
            self.response_ready.emit(response)
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            self.error.emit(f"Error processing message: {str(e)}")

class KnowledgeApp(QMainWindow):
    """Main application window for the knowledge management system."""
    
    def __init__(self):
        super().__init__()
        self.agent: Optional[KnowledgeAgent] = None
        self.indexing_thread: Optional[IndexingThread] = None
        self.chat_thread: Optional[ChatThread] = None
        
        self.init_ui()
        self.init_agent()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Knowledge Management System")
        self.setGeometry(100, 100, config.get('ui.window_width', 1000), config.get('ui.window_height', 700))
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel for controls and file management
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel for chat interface
        right_panel = self.create_chat_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (30% left, 70% right)
        splitter.setSizes([300, 700])
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        # Set application style
        self.setStyleSheet(self.get_app_stylesheet())
        
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        add_files_action = QAction('Add Documents...', self)
        add_files_action.triggered.connect(self.add_documents)
        file_menu.addAction(add_files_action)
        
        add_folder_action = QAction('Add Folder...', self)
        add_folder_action.triggered.connect(self.add_folder)
        file_menu.addAction(add_folder_action)
        
        file_menu.addSeparator()
        
        refresh_action = QAction('Refresh Index', self)
        refresh_action.triggered.connect(self.refresh_index)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction('Quit', self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_left_panel(self) -> QWidget:
        """Create the left control panel."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Title
        title_label = QLabel("Document Management")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        left_layout.addWidget(title_label)
        
        # Index statistics
        self.stats_label = QLabel("Index: Not loaded")
        self.stats_label.setWordWrap(True)
        left_layout.addWidget(self.stats_label)
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        # Buttons
        self.refresh_btn = QPushButton("Refresh Index")
        self.refresh_btn.clicked.connect(self.refresh_index)
        left_layout.addWidget(self.refresh_btn)
        
        self.add_files_btn = QPushButton("Add Documents")
        self.add_files_btn.clicked.connect(self.add_documents)
        left_layout.addWidget(self.add_files_btn)
        
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        left_layout.addWidget(self.add_folder_btn)
        
        # Configuration info
        config_label = QLabel("Configuration")
        config_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        left_layout.addWidget(config_label)
        
        # Target directories
        dirs_label = QLabel("Target Directories:")
        left_layout.addWidget(dirs_label)
        
        self.dirs_list = QListWidget()
        for directory in config.target_directories:
            self.dirs_list.addItem(directory)
        left_layout.addWidget(self.dirs_list)
        
        # Supported formats
        formats_label = QLabel(f"Supported Formats: {', '.join(config.file_extensions)}")
        formats_label.setWordWrap(True)
        left_layout.addWidget(formats_label)
        
        left_layout.addStretch()
        return left_widget
        
    def create_chat_panel(self) -> QWidget:
        """Create the chat interface panel."""
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # Title
        title_label = QLabel("Knowledge Assistant")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        chat_layout.addWidget(title_label)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlainText("Welcome! I can help you search through your indexed documents. Try asking me a question!")
        chat_layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type your question here...")
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addLayout(input_layout)
        
        return chat_widget
        
    def get_app_stylesheet(self) -> str:
        """Get the application stylesheet for macOS native look."""
        return """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QLineEdit {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0051D0;
            }
            QPushButton:pressed {
                background-color: #003f99;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
            QLabel {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            }
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
            }
        """
        
    def init_agent(self):
        """Initialize the knowledge agent."""
        try:
            self.status_bar.showMessage("Initializing knowledge agent...")
            self.agent = KnowledgeAgent()
            self.update_stats_display()
            self.status_bar.showMessage("Ready")
            logger.info("Knowledge agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            self.status_bar.showMessage("Error: Failed to initialize agent")
            QMessageBox.critical(self, "Initialization Error", 
                               f"Failed to initialize the knowledge agent:\\n{str(e)}")
    
    def update_stats_display(self):
        """Update the index statistics display."""
        if self.agent:
            stats = self.agent.query_engine.get_index_stats()
            status = stats.get('status', 'Unknown')
            doc_count = stats.get('document_count', 0)
            self.stats_label.setText(f"Index Status: {status}\\nDocuments: {doc_count}")
        
    def refresh_index(self):
        """Refresh the document index."""
        if not self.agent:
            QMessageBox.warning(self, "Error", "Agent not initialized")
            return
            
        self.start_indexing_operation("refresh")
        
    def add_documents(self):
        """Add individual documents to the index."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Documents to Add",
            "",
            f"Supported Files ({' '.join(['*' + ext for ext in config.file_extensions])})"
        )
        
        if file_paths:
            self.start_indexing_operation("add_documents", file_paths)
            
    def add_folder(self):
        """Add all documents from a folder to the index."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Add")
        
        if folder_path:
            # Find all supported files in the folder
            file_paths = []
            for ext in config.file_extensions:
                file_paths.extend(Path(folder_path).rglob(f"*{ext}"))
            
            file_paths = [str(path) for path in file_paths]
            
            if file_paths:
                self.start_indexing_operation("add_documents", file_paths)
            else:
                QMessageBox.information(self, "No Files Found", 
                                      f"No supported files found in the selected folder.\\n"
                                      f"Supported formats: {', '.join(config.file_extensions)}")
    
    def start_indexing_operation(self, operation: str, file_paths: Optional[List[str]] = None):
        """Start a background indexing operation."""
        if self.indexing_thread and self.indexing_thread.isRunning():
            QMessageBox.warning(self, "Operation in Progress", 
                              "Please wait for the current operation to complete.")
            return
            
        # Disable buttons and show progress
        self.set_indexing_ui_state(True)
        
        # Start the indexing thread
        self.indexing_thread = IndexingThread(self.agent, operation, file_paths)
        self.indexing_thread.progress.connect(self.on_indexing_progress)
        self.indexing_thread.finished.connect(self.on_indexing_finished)
        self.indexing_thread.start()
        
    def set_indexing_ui_state(self, indexing: bool):
        """Set the UI state during indexing operations."""
        self.refresh_btn.setEnabled(not indexing)
        self.add_files_btn.setEnabled(not indexing)
        self.add_folder_btn.setEnabled(not indexing)
        self.progress_bar.setVisible(indexing)
        
        if indexing:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
    def on_indexing_progress(self, message: str):
        """Handle indexing progress updates."""
        self.status_bar.showMessage(message)
        
    def on_indexing_finished(self, success: bool, message: str):
        """Handle indexing completion."""
        self.set_indexing_ui_state(False)
        self.status_bar.showMessage("Ready")
        
        if success:
            self.update_stats_display()
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Error", message)
            
    def send_message(self):
        """Send a chat message to the agent."""
        if not self.agent:
            QMessageBox.warning(self, "Error", "Agent not initialized")
            return
            
        message = self.message_input.text().strip()
        if not message:
            return
            
        # Clear input and disable send button
        self.message_input.clear()
        self.send_btn.setEnabled(False)
        self.message_input.setEnabled(False)
        
        # Add user message to chat display
        self.chat_display.append(f"\\n**You:** {message}\\n")
        self.chat_display.append("**Assistant:** Thinking...")
        
        # Start chat processing thread
        self.chat_thread = ChatThread(self.agent, message)
        self.chat_thread.response_ready.connect(self.on_chat_response)
        self.chat_thread.error.connect(self.on_chat_error)
        self.chat_thread.start()
        
    def on_chat_response(self, response: str):
        """Handle chat response."""
        # Remove the "Thinking..." message
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        
        # Add the actual response
        self.chat_display.append(response)
        self.chat_display.append("\\n" + "-"*50 + "\\n")
        
        # Re-enable input
        self.send_btn.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        
    def on_chat_error(self, error_message: str):
        """Handle chat error."""
        self.chat_display.append(f"Error: {error_message}")
        self.send_btn.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        
    def show_about(self):
        """Show the about dialog."""
        QMessageBox.about(self, "About Knowledge Management System",
                         "Knowledge Management System\\n\\n"
                         "A local document search and chat system built with:\\n"
                         "• LlamaIndex for document processing\\n"
                         "• ChromaDB for vector storage\\n"
                         "• Agno for intelligent agent reasoning\\n"
                         "• PyQt6 for native macOS interface\\n\\n"
                         "All data remains on your machine for privacy.")
        
    def closeEvent(self, event):
        """Handle application close event."""
        # Stop any running threads
        if self.indexing_thread and self.indexing_thread.isRunning():
            self.indexing_thread.terminate()
            self.indexing_thread.wait()
            
        if self.chat_thread and self.chat_thread.isRunning():
            self.chat_thread.terminate()
            self.chat_thread.wait()
            
        event.accept()

def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Knowledge Management System")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = KnowledgeApp()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
