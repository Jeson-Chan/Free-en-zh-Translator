import { useState } from 'react';
import TabBar, { Tab } from './components/TabBar';
import TranslateView from './components/TranslateView';
import HistoryView from './components/HistoryView';
import ModesView from './components/ModesView';
import SettingsView from './components/SettingsView';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('translate');

  return (
    <div
      className="flex flex-col min-h-screen max-w-md mx-auto"
      style={{ backgroundColor: '#E8E2D9' }}
    >
      <div className="flex-1 overflow-hidden flex flex-col" style={{ minHeight: 0 }}>
        {activeTab === 'translate' && <TranslateView />}
        {activeTab === 'history' && <HistoryView />}
        {activeTab === 'modes' && <ModesView />}
        {activeTab === 'settings' && <SettingsView />}
      </div>
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
}
