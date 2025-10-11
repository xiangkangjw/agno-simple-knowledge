import { ThemeProvider } from "@/components/theme-provider"
import { AppLayout } from "@/components/layout/AppLayout"
import { ChatInterface } from "@/components/chat/ChatInterface"
import { DocumentManager } from "@/components/documents/DocumentManager"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { MessageSquare, FileText } from "lucide-react"

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="knowledge-app-theme">
      <AppLayout>
        <div className="container mx-auto p-6">
          <Tabs defaultValue="chat" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="chat" className="flex items-center space-x-2">
                <MessageSquare className="h-4 w-4" />
                <span>Chat</span>
              </TabsTrigger>
              <TabsTrigger value="documents" className="flex items-center space-x-2">
                <FileText className="h-4 w-4" />
                <span>Documents</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="mt-6">
              <div className="grid gap-6 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <ChatInterface />
                </div>
                <div className="space-y-6">
                  <DocumentManager />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="documents" className="mt-6">
              <DocumentManager />
            </TabsContent>
          </Tabs>
        </div>
      </AppLayout>
    </ThemeProvider>
  )
}

export default App