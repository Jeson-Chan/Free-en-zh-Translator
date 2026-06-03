import { Clock, ChevronRight } from 'lucide-react';

const SAMPLE_HISTORY = [
  { id: 1, source: 'The quick brown fox jumps over the lazy dog.', translated: '敏捷的棕色狐狸跳过了懒惰的狗。', mode: 'Academic', time: '2 min ago' },
  { id: 2, source: '知识就是力量。', translated: 'Knowledge is power.', mode: 'Literary', time: '1 hr ago' },
  { id: 3, source: 'Please find attached the revised proposal.', translated: '请见附件中修改后的提案。', mode: 'Business', time: 'Yesterday' },
];

export default function HistoryView() {
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
          history
        </h1>
      </div>

      {SAMPLE_HISTORY.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-8">
          <Clock size={48} strokeWidth={1} style={{ color: '#B8AFA6' }} />
          <p style={{ fontFamily: "'Lora', Georgia, serif", fontSize: '18px', color: '#8C7B6E', textAlign: 'center' }}>
            Your translation history will appear here.
          </p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-5 flex flex-col gap-3 pb-4">
          {SAMPLE_HISTORY.map(item => (
            <button
              key={item.id}
              className="w-full rounded-2xl p-4 text-left transition-all duration-200 active:scale-[0.98] flex items-start justify-between gap-3"
              style={{
                backgroundColor: '#F0EBE4',
                border: '1px solid #D4CCC4',
                cursor: 'pointer',
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="px-2.5 py-0.5 rounded-full"
                    style={{
                      backgroundColor: '#D4CCC4',
                      color: '#5C3D2B',
                      fontFamily: "'Lora', Georgia, serif",
                      fontSize: '11px',
                      fontWeight: 500,
                    }}
                  >
                    {item.mode}
                  </span>
                  <span
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: '11px',
                      color: '#B8AFA6',
                    }}
                  >
                    {item.time}
                  </span>
                </div>
                <p
                  className="truncate mb-1"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: '14px',
                    color: '#2C1F14',
                    lineHeight: '1.5',
                  }}
                >
                  {item.source}
                </p>
                <p
                  className="truncate"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: '13px',
                    color: '#8C7B6E',
                    lineHeight: '1.5',
                  }}
                >
                  {item.translated}
                </p>
              </div>
              <ChevronRight size={18} strokeWidth={1.5} style={{ color: '#B8AFA6', flexShrink: 0, marginTop: '2px' }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
