import { useState, useEffect } from 'react';
import { Layout } from './components/Layout';
import { Chat } from './components/Chat';
import { Memory } from './components/Memory';
import { Statistics } from './components/Statistics';
import { Settings } from './components/Settings';
import { endpoints } from './lib/api';

function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    createSession();
  }, []);

  const createSession = async () => {
    try {
      const response = await endpoints.createSession();
      setSessionId(response.data.session_id);
    } catch (error) {
      console.error('Failed to create session:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !sessionId) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Initializing Memory Agent...</p>
        </div>
      </div>
    );
  }

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'chat' && <Chat sessionId={sessionId} />}
      {activeTab === 'memory' && <Memory />}
      {activeTab === 'stats' && <Statistics />}
      {activeTab === 'settings' && <Settings />}
    </Layout>
  );
}

export default App;