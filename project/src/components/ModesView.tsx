import { useState } from 'react';
import { Check } from 'lucide-react';

const MODES = [
  { id: 'Academic', title: 'Academic', description: 'Formal scholarly language with precise terminology.' },
  { id: 'Casual', title: 'Casual', description: 'Everyday conversational tone, natural and relaxed.' },
  { id: 'Business', title: 'Business', description: 'Professional workplace communication.' },
  { id: 'Literary', title: 'Literary', description: 'Expressive, narrative-driven prose with stylistic flair.' },
];

export default function ModesView() {
  const [selected, setSelected] = useState('Academic');

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#E8E2D9' }}>
      <div className="px-5 pt-7 pb-2">
        <h1
          style={{
            fontFamily: "'Lora', Georgia, serif",
            fontSize: '28px',
            fontWeight: 700,
            color: '#2C1F14',
            letterSpacing: '-0.3px',
          }}
        >
          modes
        </h1>
        <p
          className="mt-1"
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '14px',
            color: '#8C7B6E',
            lineHeight: '1.5',
          }}
        >
          Choose your preferred translation style.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 pt-4 flex flex-col gap-3 pb-4">
        {MODES.map(mode => (
          <button
            key={mode.id}
            onClick={() => setSelected(mode.id)}
            className="w-full rounded-2xl p-4 text-left transition-all duration-200 active:scale-[0.98] flex items-center justify-between gap-3"
            style={{
              backgroundColor: selected === mode.id ? '#3E2B1F' : '#F0EBE4',
              border: `1px solid ${selected === mode.id ? '#3E2B1F' : '#D4CCC4'}`,
              cursor: 'pointer',
            }}
          >
            <div>
              <p
                style={{
                  fontFamily: "'Lora', Georgia, serif",
                  fontSize: '17px',
                  fontWeight: 500,
                  color: selected === mode.id ? '#F0EBE4' : '#2C1F14',
                  marginBottom: '4px',
                }}
              >
                {mode.title}
              </p>
              <p
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: '13px',
                  color: selected === mode.id ? '#C4B9B0' : '#8C7B6E',
                  lineHeight: '1.4',
                }}
              >
                {mode.description}
              </p>
            </div>
            {selected === mode.id && (
              <div
                className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                style={{ backgroundColor: '#F0EBE4' }}
              >
                <Check size={14} strokeWidth={2.5} style={{ color: '#3E2B1F' }} />
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
