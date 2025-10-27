import { useState, useEffect } from "react";
import { Brain, Settings, Activity } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, SystemStatus } from "@/lib/api";

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSystemStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(loadSystemStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadSystemStatus = async () => {
    try {
      setError(null);
      const status = await api.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.error('Failed to load system status:', err);
      setError(err instanceof Error ? err.message : 'Failed to load system status');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (isLoading) {
      return <Badge variant="secondary">Loading...</Badge>;
    }
    if (error) {
      return <Badge variant="destructive">Error</Badge>;
    }
    if (systemStatus?.status === 'ready') {
      return <Badge variant="default">Ready</Badge>;
    }
    return <Badge variant="secondary">Not Ready</Badge>;
  };

  const getDocumentCount = () => {
    return (systemStatus?.index_stats?.source_file_count ?? systemStatus?.index_stats?.document_count) || 0;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex h-16 items-center justify-between px-6">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <Brain className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-semibold">Knowledge Management</h1>
            </div>
            {getStatusBadge()}
            {systemStatus?.status === 'ready' && (
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <Activity className="h-4 w-4" />
                <span>{getDocumentCount()} files</span>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={loadSystemStatus}
              disabled={isLoading}
            >
              <Activity className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <ThemeToggle />
            <Button variant="outline" size="icon">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-destructive/10 border-b border-destructive/20 px-6 py-3">
          <div className="flex items-center space-x-2">
            <div className="h-2 w-2 rounded-full bg-destructive" />
            <span className="text-sm text-destructive">
              Backend connection failed: {error}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={loadSystemStatus}
              className="ml-auto"
            >
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>
    </div>
  );
}
