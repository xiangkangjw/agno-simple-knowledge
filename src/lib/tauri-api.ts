/**
 * Tauri API bindings for frontend-backend communication
 */

import { invoke } from '@tauri-apps/api/core';

// Tauri command bindings
export const tauriApi = {
  // Backend management
  startPythonBackend: (): Promise<string> => invoke('start_python_backend'),
  checkBackendHealth: (): Promise<boolean> => invoke('check_backend_health'),

  // File system operations (to be implemented)
  openFileDialog: async (): Promise<string[]> => {
    // TODO: Implement with @tauri-apps/plugin-dialog
    console.log('File dialog would open here');
    return [];
  },

  openFolderDialog: async (): Promise<string> => {
    // TODO: Implement with @tauri-apps/plugin-dialog
    console.log('Folder dialog would open here');
    return '';
  },

  // Utility functions
  greet: (name: string): Promise<string> => invoke('greet', { name }),
};

export default tauriApi;