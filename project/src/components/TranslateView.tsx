import { useState, useRef } from 'react';
import { Clipboard, Copy, ArrowLeftRight } from 'lucide-react';

const MODES = ['Academic', 'Casual', 'Business', 'Literary'];

export default function TranslateView() {
  const [sourceText, setSourceText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [activeMode, setActiveMode] = useState('Academic');
  const [isLoading, setIsLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const sourceRef = useRef<HTMLTextAreaElement>(null);

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setSourceText(text);
      setStatusMsg('Clipboard content pasted.');
      setTimeout(() => setStatusMsg(''), 2500);
    } catch {
      setStatusMsg('Unable to access clipboard.');
      setTimeout(() => setStatusMsg(''), 2500);
    }
  };

  const handleCopy = async () => {
    if (!translatedText) return;
    try {
      await navigator.clipboard.writeText(translatedText);
      setStatusMsg('Translation copied.');
      setTimeout(() => setStatusMsg(''), 2500);
    } catch {
      setStatusMsg('Unable to copy.');
      setTimeout(() => setStatusMsg(''), 2500);
    }
  };

  const handleTranslate = async () => {
    if (!sourceText.trim()) return;
    setIsLoading(true);
    setStatusMsg('Translating...');
    await new Promise(r => setTimeout(r, 1200));
    setTranslatedText(`[${activeMode} translation of: "${sourceText.trim()}" — connect your API to enable real translation.]`);
    setIsLoading(false);
    setStatusMsg('');
  };

  const handleSwap = () => {
    setSourceText(translatedText);
    setTranslatedText(sourceText);
  };

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
          translator
        </h1>
      </div>

      <div
        className="mx-5 mb-4 flex gap-2 overflow-x-auto pb-1"
        style={{ scrollbarWidth: 'none' }}
      >
        {MODES.map(mode => (
          <button
            key={mode}
            onClick={() => setActiveMode(mode)}
            className="flex-shrink-0 px-4 py-1.5 rounded-full transition-all duration-200"
            style={{
              backgroundColor: activeMode === mode ? '#3E2B1F' : '#D4CCC4',
              color: activeMode === mode ? '#F0EBE4' : '#5C4033',
              fontFamily: "'Lora', Georgia, serif",
              fontSize: '13px',
              fontWeight: activeMode === mode ? 500 : 400,
              border: 'none',
              cursor: 'pointer',
              letterSpacing: '0.1px',
            }}
          >
            {mode}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-5 flex flex-col gap-4 pb-4">
        <div
          className="rounded-2xl overflow-hidden"
          style={{ backgroundColor: '#F0EBE4', border: '1px solid #D4CCC4' }}
        >
          <div className="flex items-center justify-between px-4 pt-3 pb-2">
            <span
              style={{
                fontFamily: "'Lora', Georgia, serif",
                fontSize: '12px',
                fontWeight: 500,
                color: '#8C7B6E',
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
              }}
            >
              Source Text
            </span>
            <button
              onClick={handlePaste}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full transition-all duration-200 active:scale-95"
              style={{
                backgroundColor: '#D4CCC4',
                border: 'none',
                cursor: 'pointer',
                color: '#5C3D2B',
              }}
            >
              <Clipboard size={13} strokeWidth={1.8} />
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '12px', fontWeight: 500 }}>
                Paste
              </span>
            </button>
          </div>
          <textarea
            ref={sourceRef}
            value={sourceText}
            onChange={e => setSourceText(e.target.value)}
            placeholder="Paste English or Chinese text here..."
            rows={6}
            className="w-full px-4 pb-4 outline-none"
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              color: '#2C1F14',
              fontSize: '15px',
              lineHeight: '1.6',
              fontFamily: "'Inter', sans-serif",
            }}
          />
        </div>

        <div className="flex items-center justify-center">
          <button
            onClick={handleSwap}
            className="flex items-center gap-2 px-4 py-2 rounded-full transition-all duration-200 active:scale-95"
            style={{
              backgroundColor: '#D4CCC4',
              border: 'none',
              cursor: 'pointer',
              color: '#5C3D2B',
            }}
          >
            <ArrowLeftRight size={15} strokeWidth={1.8} />
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '13px', fontWeight: 500 }}>
              Swap
            </span>
          </button>
        </div>

        <button
          onClick={handleTranslate}
          disabled={isLoading || !sourceText.trim()}
          className="w-full py-4 rounded-2xl transition-all duration-200 active:scale-[0.98]"
          style={{
            backgroundColor: sourceText.trim() ? '#3E2B1F' : '#B8AFA6',
            color: '#F0EBE4',
            border: 'none',
            cursor: sourceText.trim() ? 'pointer' : 'default',
            fontFamily: "'Lora', Georgia, serif",
            fontSize: '17px',
            fontWeight: 500,
            letterSpacing: '0.2px',
          }}
        >
          {isLoading ? 'Translating...' : 'Translate'}
        </button>

        <div
          className="rounded-2xl overflow-hidden"
          style={{ backgroundColor: '#F0EBE4', border: '1px solid #D4CCC4' }}
        >
          <div className="flex items-center justify-between px-4 pt-3 pb-2">
            <span
              style={{
                fontFamily: "'Lora', Georgia, serif",
                fontSize: '12px',
                fontWeight: 500,
                color: '#8C7B6E',
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
              }}
            >
              Translated Text
            </span>
            {translatedText && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1 rounded-full transition-all duration-200 active:scale-95"
                style={{
                  backgroundColor: '#D4CCC4',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#5C3D2B',
                }}
              >
                <Copy size={13} strokeWidth={1.8} />
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '12px', fontWeight: 500 }}>
                  Copy
                </span>
              </button>
            )}
          </div>
          <div
            className="px-4 pb-4 min-h-[120px]"
            style={{
              color: translatedText ? '#2C1F14' : '#B8AFA6',
              fontSize: '15px',
              lineHeight: '1.6',
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {translatedText || 'Translation result appears here. Tap to copy.'}
          </div>
        </div>
      </div>

      {statusMsg && (
        <div
          className="mx-5 mb-3 px-4 py-2.5 rounded-xl text-center"
          style={{
            backgroundColor: '#3E2B1F',
            color: '#F0EBE4',
            fontFamily: "'Inter', sans-serif",
            fontSize: '13px',
          }}
        >
          {statusMsg}
        </div>
      )}
    </div>
  );
}
