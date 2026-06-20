import React, { useState, useRef, useEffect } from 'react';

// Loads two Google Fonts once: Space Grotesk for display type, JetBrains Mono for the console/log.
function useForgeFonts() {
  useEffect(() => {
    if (document.getElementById('forge-fonts')) return;
    const link = document.createElement('link');
    link.id = 'forge-fonts';
    link.rel = 'stylesheet';
    link.href =
      'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap';
    document.head.appendChild(link);
  }, []);
}

const LEVEL_STYLES = {
  info: 'text-slate-400',
  queuing: 'text-amber-400',
  processing: 'text-amber-400',
  completed: 'text-emerald-400',
  error: 'text-rose-400',
  warning: 'text-rose-300',
};

const LEVEL_TAG = {
  info: 'INFO',
  queuing: 'QUEUED',
  processing: 'BUILD',
  completed: 'DONE',
  error: 'ERROR',
  warning: 'WARN',
};

function timestamp() {
  const d = new Date();
  return d.toTimeString().slice(0, 8);
}

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState('idle'); // idle, queuing, processing, completed, error
  const [message, setMessage] = useState('');
  const [jobId, setJobId] = useState(null);
  const [logs, setLogs] = useState([]);

  const eventSourceRef = useRef(null);
  const logEndRef = useRef(null);

  useForgeFonts();

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [logs]);

  const pushLog = (level, text) => {
    setLogs((prev) => [...prev, { time: timestamp(), level, text }]);
  };

  const resetAll = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStatus('idle');
    setMessage('');
    setJobId(null);
    setLogs([]);
  };

  const handleClear = () => {
    if (status === 'queuing' || status === 'processing') {
      // Only clear the input while a job is actively running; leave the console intact.
      setPrompt('');
      return;
    }
    setPrompt('');
    resetAll();
  };

  const handleStop = async (id) => {
    const targetId = id || jobId;
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    pushLog('warning', 'Build stopped by user.');
    setStatus('idle');
    setMessage('Generation stopped.');

    if (targetId) {
      try {
        await fetch(`/api/cancel/${targetId}`, { method: 'POST' });
      } catch (err) {
        // Best-effort cancellation; the stream is already closed client-side.
        console.error('Cancel request failed:', err);
      }
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setStatus('queuing');
    setMessage('Submitting prompt to server...');
    setJobId(null);
    setLogs([]);
    pushLog('queuing', 'Submitting prompt to server...');

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }

      const { job_id } = await response.json();
      // Save the job id immediately — this is the id we'll use to download the zip later,
      // regardless of what the stream payload contains.
      setJobId(job_id);
      pushLog('info', `Job accepted: ${job_id}`);

      connectToStream(job_id);
    } catch (error) {
      console.error('Submission failed:', error);
      setStatus('error');
      setMessage('Failed to connect to the server. Please try again.');
      pushLog('error', 'Failed to connect to the server.');
    }
  };

  const connectToStream = (id) => {
    eventSourceRef.current = new EventSource(`/api/stream/${id}`);

    eventSourceRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        setStatus(data.status);
        setMessage(data.message);
        pushLog(data.status || 'info', data.message || '');

        if (data.status === 'completed') {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
          pushLog('completed', `Archive ready for job ${id}.`);
        } else if (data.status === 'error') {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    eventSourceRef.current.onerror = (error) => {
      console.error('SSE connection lost or failed:', error);
      setStatus('error');
      setMessage('Lost connection to the server stream.');
      pushLog('error', 'Lost connection to the server stream.');
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  };

  const isRunning = status === 'queuing' || status === 'processing';
  const downloadUrl = jobId ? `/api/download/${jobId}` : null;

  return (
    <div
      className="min-h-screen bg-slate-100 flex flex-col items-center py-14 px-4 sm:px-6 lg:px-8"
      style={{ fontFamily: "'Space Grotesk', sans-serif" }}
    >
      <div className="max-w-2xl w-full">

        {/* Header */}
        <div className="mb-6 text-center">
          <div
            className="inline-block px-3 py-1 mb-4 rounded-full bg-slate-900 text-amber-400 text-xs tracking-widest uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            build console
          </div>
          <h1 className="text-3xl sm:text-4xl font-semibold text-slate-900 tracking-tight mb-2">
            Application Generator
          </h1>
          <p className="text-slate-500 text-sm max-w-lg mx-auto">
            Describe the application you want. The backend compiles source code and packages
            it into a downloadable zip.
          </p>
        </div>

        {/* Main card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <form onSubmit={handleGenerate} className="p-6 sm:p-8 space-y-4">
            <label
              htmlFor="prompt"
              className="block text-xs font-medium text-slate-500 uppercase tracking-wide"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              Prompt
            </label>
            <textarea
              id="prompt"
              rows={7}
              className="w-full p-4 border border-slate-300 rounded-xl resize-y bg-white focus:ring-2 focus:ring-amber-500 focus:border-amber-500 transition-colors text-slate-800 placeholder-slate-400 disabled:bg-slate-50 disabled:text-slate-400"
              placeholder="e.g., Create a REST API using Express and MongoDB with user authentication, JWT sessions, and a Postgres data layer..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={isRunning}
            />

            <div className="flex flex-col sm:flex-row gap-3 pt-1">
              <button
                type="submit"
                disabled={!prompt.trim() || isRunning}
                className="flex-1 flex justify-center items-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold text-slate-900 bg-amber-400 hover:bg-amber-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isRunning ? 'Generating…' : 'Generate code'}
              </button>

              <button
                type="button"
                onClick={() => handleStop()}
                disabled={!isRunning}
                className="flex-1 sm:flex-none flex justify-center items-center gap-2 py-3 px-5 rounded-xl text-sm font-semibold text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rose-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Stop
              </button>

              <button
                type="button"
                onClick={handleClear}
                disabled={!prompt.trim() && status === 'idle'}
                className="flex-1 sm:flex-none flex justify-center items-center gap-2 py-3 px-5 rounded-xl text-sm font-semibold text-slate-600 bg-slate-50 border border-slate-200 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Clear
              </button>
            </div>
          </form>

          {/* Terminal-style build console */}
          {(logs.length > 0 || status !== 'idle') && (
            <div className="border-t border-slate-200 bg-slate-950 px-5 py-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500/70" />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400/70" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
                </div>
                <span
                  className="text-[11px] text-slate-500 uppercase tracking-widest"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {jobId ? `job ${jobId}` : 'no active job'}
                </span>
              </div>

              <div
                className="h-40 overflow-y-auto text-xs leading-relaxed pr-1"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                {logs.map((log, i) => (
                  <div key={i} className="flex gap-2 whitespace-pre-wrap break-words">
                    <span className="text-slate-600 shrink-0">{log.time}</span>
                    <span className={`shrink-0 ${LEVEL_STYLES[log.level] || 'text-slate-400'}`}>
                      [{LEVEL_TAG[log.level] || 'INFO'}]
                    </span>
                    <span className="text-slate-300">{log.text}</span>
                  </div>
                ))}
                {isRunning && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-slate-600">{timestamp()}</span>
                    <span className="text-amber-400">[BUILD]</span>
                    <span className="inline-block w-2 h-3.5 bg-amber-400 animate-pulse" />
                  </div>
                )}
                <div ref={logEndRef} />
              </div>
            </div>
          )}

          {/* Result footer */}
          {(status === 'completed' || status === 'error') && (
            <div
              className={`px-6 sm:px-8 py-4 border-t flex items-center justify-between gap-4 ${
                status === 'completed'
                  ? 'bg-emerald-50 border-emerald-100'
                  : 'bg-rose-50 border-rose-100'
              }`}
            >
              <p
                className={`text-sm ${
                  status === 'completed' ? 'text-emerald-700' : 'text-rose-700'
                }`}
              >
                {status === 'completed' ? message || 'Build complete.' : message || 'Build failed.'}
              </p>

              {status === 'completed' && downloadUrl && (
                <a
                  href={downloadUrl}
                  className="shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
                    <path d="M12 16.5l4.5-4.5h-3V3.75h-3V12H7.5l4.5 4.5z" />
                    <path d="M5.25 18.75h13.5V21H5.25v-2.25z" />
                  </svg>
                  Download zip
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
