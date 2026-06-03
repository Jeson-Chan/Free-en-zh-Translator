import { useState } from 'react';
import { ChevronRight, Globe, Moon, Bell, Info } from 'lucide-react';

const SECTIONS = [
  {
    title: 'Preferences',
    items: [
      { label: 'Language Pair', value: 'EN → ZH', Icon: Globe, hasArrow: true },
      { label: 'Dark Mode', value: '', Icon: Moon, isToggle: true },
      { label: 'Notifications', value: '', Icon: Bell, isToggle: false, hasArrow: true },
    ],
  },
  {
    title: 'About',
    items: [
      { label: 'Version', value: '1.0.0', Icon: Info, hasArrow: false },
    ],
  },
];

export default function SettingsView() {
  const [darkMode, setDarkMode] = useState(false);

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#E8E2D9' }}>
      <div className="px-5 pt-7 pb-4">
        <h1
          style={{
            fontFamily: "'Lora', Georgia, serif",
            fontSize: '28px',
            fontWeight: 700,
            color: '#2C1F14',
            letterSpacing: '-0.3px',
          }}
        >
          settings
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto px-5 flex flex-col gap-6 pb-4">
        {SECTIONS.map(section => (
          <div key={section.title}>
            <p
              className="mb-2 px-1"
              style={{
                fontFamily: "'Lora', Georgia, serif",
                fontSize: '12px',
                fontWeight: 500,
                color: '#8C7B6E',
                textTransform: 'uppercase',
                letterSpacing: '0.6px',
              }}
            >
              {section.title}
            </p>
            <div
              className="rounded-2xl overflow-hidden"
              style={{ backgroundColor: '#F0EBE4', border: '1px solid #D4CCC4' }}
            >
              {section.items.map((item, i) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between px-4 py-3.5 transition-all duration-150"
                  style={{
                    borderTop: i > 0 ? '1px solid #E4DDD6' : 'none',
                    cursor: item.hasArrow ? 'pointer' : 'default',
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: '#D4CCC4' }}
                    >
                      <item.Icon size={16} strokeWidth={1.8} style={{ color: '#5C3D2B' }} />
                    </div>
                    <span
                      style={{
                        fontFamily: "'Inter', sans-serif",
                        fontSize: '15px',
                        color: '#2C1F14',
                      }}
                    >
                      {item.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.value && (
                      <span
                        style={{
                          fontFamily: "'Inter', sans-serif",
                          fontSize: '14px',
                          color: '#8C7B6E',
                        }}
                      >
                        {item.value}
                      </span>
                    )}
                    {item.isToggle ? (
                      <button
                        onClick={() => setDarkMode(v => !v)}
                        className="relative w-11 h-6 rounded-full transition-all duration-300"
                        style={{
                          backgroundColor: darkMode ? '#3E2B1F' : '#D4CCC4',
                          border: 'none',
                          cursor: 'pointer',
                          padding: 0,
                        }}
                      >
                        <div
                          className="absolute top-0.5 w-5 h-5 rounded-full transition-all duration-300"
                          style={{
                            backgroundColor: '#F0EBE4',
                            left: darkMode ? 'calc(100% - 22px)' : '2px',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                          }}
                        />
                      </button>
                    ) : item.hasArrow ? (
                      <ChevronRight size={18} strokeWidth={1.5} style={{ color: '#B8AFA6' }} />
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        <div className="flex flex-col items-center gap-1 pt-4 pb-8">
          <p
            style={{
              fontFamily: "'Lora', Georgia, serif",
              fontSize: '20px',
              fontWeight: 700,
              color: '#2C1F14',
            }}
          >
            translator
          </p>
          <p
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '12px',
              color: '#B8AFA6',
            }}
          >
            Version 1.0.0
          </p>
        </div>
      </div>
    </div>
  );
}
