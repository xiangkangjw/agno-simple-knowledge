import { useState, useEffect, useCallback } from "react";
import {
  FileText,
  RefreshCw,
  Plus,
  FolderOpen,
  Upload,
  Database,
  AlertCircle,
  CheckCircle2,
  Clock
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { api, SystemStatus } from "@/lib/api";

interface DocumentStats {
  status: string;
  document_count: number;
  source_file_count?: number;
  storage_path?: string;
  collection_name?: string;
}

interface DocumentManagerProps {
  className?: string;
}

export function DocumentManager({ className }: DocumentManagerProps) {
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
    loadSystemStatus();
  }, []);

  const loadStats = async () => {
    try {
      setError(null);
      const docStats = await api.getDocumentStats();
      setStats(docStats);
    } catch (err) {
      console.error('Failed to load document stats:', err);
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    }
  };

  const loadSystemStatus = async () => {
    try {
      const status = await api.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.error('Failed to load system status:', err);
    }
  };

  const refreshIndex = async () => {
    setIsRefreshing(true);
    try {
      setError(null);
      const result = await api.refreshIndex();
      if (result.success) {
        await loadStats();
        await loadSystemStatus();
      } else {
        setError(result.error || 'Failed to refresh index');
      }
    } catch (err) {
      console.error('Failed to refresh index:', err);
      setError(err instanceof Error ? err.message : 'Failed to refresh index');
    } finally {
      setIsRefreshing(false);
    }
  };

  const openFileDialog = async () => {
    // Note: This would need to be implemented with Tauri's file dialog API
    // For now, we'll show a placeholder
    console.log('File dialog would open here');
    // TODO: Implement with @tauri-apps/plugin-dialog
  };

  const openFolderDialog = async () => {
    // Note: This would need to be implemented with Tauri's folder dialog API
    console.log('Folder dialog would open here');
    // TODO: Implement with @tauri-apps/plugin-dialog
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);

    // Note: File drop handling would need to be implemented with Tauri APIs
    const files = Array.from(e.dataTransfer.files);
    console.log('Files dropped:', files);
    // TODO: Implement file processing
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  }, []);

  const getStatusIcon = () => {
    if (!stats) return <Clock className="h-4 w-4" />;

    switch (stats.status) {
      case 'Index loaded':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case 'No index loaded':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getTargetDirectories = () => {
    return systemStatus?.target_directories || [];
  };

  const getSupportedFormats = () => {
    return systemStatus?.supported_formats || [];
  };

  return (
    <div className={className}>
      <div className="space-y-6">
        {/* Document Index Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center space-x-2">
                  <Database className="h-5 w-5" />
                  <span>Document Index</span>
                </CardTitle>
                <CardDescription>
                  Status and statistics for your document collection
                </CardDescription>
              </div>
              <Button
                onClick={refreshIndex}
                disabled={isRefreshing}
                variant="outline"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh Index
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 rounded-md bg-destructive/10 border border-destructive/20">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="h-4 w-4 text-destructive" />
                  <span className="text-sm text-destructive">{error}</span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Status */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  {getStatusIcon()}
                  <span className="text-sm font-medium">Status</span>
                </div>
                <Badge variant={stats?.status === 'Index loaded' ? 'default' : 'secondary'}>
                  {stats?.status || 'Loading...'}
                </Badge>
              </div>

              {/* Source Files Count */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4" />
                  <span className="text-sm font-medium">Files</span>
                </div>
                <div className="text-2xl font-bold">
                  {(stats?.source_file_count ?? stats?.document_count) || 0}
                </div>
              </div>

              {/* Storage Path */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <FolderOpen className="h-4 w-4" />
                  <span className="text-sm font-medium">Storage</span>
                </div>
                <div className="text-sm text-muted-foreground truncate">
                  {stats?.collection_name || 'Not available'}
                </div>
              </div>
            </div>

            {isRefreshing && (
              <div className="mt-4">
                <Progress className="h-2" />
                <p className="text-sm text-muted-foreground mt-2">
                  Refreshing document index...
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Add Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Plus className="h-5 w-5" />
              <span>Add Documents</span>
            </CardTitle>
            <CardDescription>
              Add individual files or entire folders to your knowledge base
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Drag and Drop Area */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? 'border-primary bg-primary/5'
                  : 'border-muted-foreground/25 hover:border-muted-foreground/50'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">
                {dragActive ? 'Drop files here' : 'Drag & drop files here'}
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Or use the buttons below to select files or folders
              </p>

              <div className="flex justify-center space-x-4">
                <Button onClick={openFileDialog}>
                  <FileText className="h-4 w-4 mr-2" />
                  Select Files
                </Button>
                <Button onClick={openFolderDialog} variant="outline">
                  <FolderOpen className="h-4 w-4 mr-2" />
                  Select Folder
                </Button>
              </div>
            </div>

            <Separator className="my-4" />

            {/* Configuration Info */}
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Target Directories</h4>
                <div className="space-y-1">
                  {getTargetDirectories().length > 0 ? (
                    getTargetDirectories().map((dir, index) => (
                      <div key={index} className="text-sm text-muted-foreground font-mono">
                        {dir}
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-muted-foreground">No directories configured</div>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-2">Supported Formats</h4>
                <div className="flex flex-wrap gap-2">
                  {getSupportedFormats().map((format, index) => (
                    <Badge key={index} variant="outline">
                      {format}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common document management tasks
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Button
                variant="outline"
                className="h-auto p-4 justify-start"
                onClick={() => console.log('Open configuration')}
              >
                <div className="text-left">
                  <div className="font-medium">Configure Directories</div>
                  <div className="text-sm text-muted-foreground">
                    Set up which folders to monitor
                  </div>
                </div>
              </Button>

              <Button
                variant="outline"
                className="h-auto p-4 justify-start"
                onClick={() => console.log('View storage location')}
              >
                <div className="text-left">
                  <div className="font-medium">View Storage</div>
                  <div className="text-sm text-muted-foreground">
                    Open the database storage location
                  </div>
                </div>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
