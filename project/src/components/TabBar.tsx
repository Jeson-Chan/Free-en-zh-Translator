import { Home, Clock, Layers, Settings, TableProperties as LucideProps } from 'lucide-react';
import { FC } from 'react';

export type Tab = 'translate' | 'history' | 'modes' | 'settings';

interface TabBarProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

const tabs: { id: Tab; label: string; Icon: FC<LucideProps> }[] = [
  { id: 'translate', label: 'Translate', Icon: Home },
  { id: 'history', label: 'History', Icon: Clock },
  { id: 'modes', label: 'Modes', Icon: Layers },
  { id: 'settings', label: 'Settings', Icon: Settings },
];

export default function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <div
      style={{ backgroundColor: '#F0EBE4', borderTop: '1px solid #D4CCC4' }}
      className="flex items-center justify-around px-2 pt-3 pb-6"
    >
      {tabs.map(({ id, label, Icon }) => {
        const active = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className="flex flex-col items-center gap-1 min-w-[60px] transition-all duration-200"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          >
            <div
              className="flex items-center justify-center w-14 h-9 rounded-full transition-all duration-200"
              style={{ backgroundColor: active ? '#D4CCC4' : 'transparent' }}
            >
              <Icon
                size={22}
                strokeWidth={active ? 2 : 1.5}
                style={{ color: active ? '#2C1F14' : '#8C7B6E' }}
              />
            </div>
            <span
              style={{
                fontFamily: "'Inter', sans-serif",
                color: active ? '#2C1F14' : '#8C7B6E',
                fontWeight: active ? 500 : 400,
                fontSize: '11px',
              }}
            >
              {label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
