import React, { useState, useRef, useEffect } from 'react';

export default function App() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState('idle'); // idle, queuing, processing, completed, error
  const [message, setMessage] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);
  
  // Use a ref to hold the EventSource so we can close it from anywhere
  const eventSourceRef = useRef(null);

  // Cleanup EventSource when the component unmounts
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    // Reset state for a new job
    setStatus('queuing');
    setMessage('Submitting prompt to server...');
    setDownloadUrl(null);
    
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // 1. Start the job via standard HTTP POST
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ "prompt":prompt }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status: ${response.status}`);
      }

      const { job_id } = await response.json();

      // 2. Initialize the SSE Connection
      connectToStream(job_id);

    } catch (error) {
      console.error('Submission failed:', error);
      setStatus('error');
      setMessage('Failed to connect to the server. Please try again.');
    }
  };

  const connectToStream = (jobId) => {
    eventSourceRef.current = new EventSource(`/api/stream/${jobId}`);

    // Standard message event handler
    eventSourceRef.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        setStatus(data.status);
        setMessage(data.message);

        if (data.status === 'completed') {
          eventSourceRef.current.close();
          setDownloadUrl(data.download_url);
          
          // Optional: Automatically trigger download
          window.location.href = data.download_url;
        } 
        else if (data.status === 'error') {
          eventSourceRef.current.close();
        }
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    // Explicit error handler for the SSE connection
    eventSourceRef.current.onerror = (error) => {
      console.error('SSE connection lost or failed:', error);
      setStatus('error');
      setMessage('Lost connection to the server stream.');
      eventSourceRef.current.close();
    };
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full space-y-8 bg-white p-8 rounded-xl shadow-sm border border-gray-100">
        
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Application Generator</h2>
          <p className="text-gray-500 text-sm">Describe the application you want, and the backend will compile the source code into a zip file.</p>
        </div>

        <form onSubmit={handleGenerate} className="space-y-4">
          <textarea
            className="w-full h-32 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            placeholder="e.g., Create a REST API using Express and MongoDB with user authentication..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={status === 'queuing' || status === 'processing'}
          />
          
          <button
            type="submit"
            disabled={!prompt.trim() || status === 'queuing' || status === 'processing'}
            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {status === 'queuing' || status === 'processing' ? 'Generating...' : 'Generate Code'}
          </button>
        </form>

        {/* Dynamic Status UI */}
        {status !== 'idle' && (
          <div className={`mt-6 p-4 rounded-lg border ${
            status === 'error' ? 'bg-red-50 border-red-200' : 
            status === 'completed' ? 'bg-green-50 border-green-200' : 
            'bg-blue-50 border-blue-200'
          }`}>
            <div className="flex items-center space-x-3">
              {/* Simple CSS loading spinner */}
              {(status === 'queuing' || status === 'processing') && (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              )}
              
              <div className="flex-1">
                <h3 className={`text-sm font-medium ${
                  status === 'error' ? 'text-red-800' : 
                  status === 'completed' ? 'text-green-800' : 
                  'text-blue-800'
                }`}>
                  Status: {status.charAt(0).toUpperCase() + status.slice(1)}
                </h3>
                <p className={`text-sm mt-1 ${
                  status === 'error' ? 'text-red-600' : 
                  status === 'completed' ? 'text-green-600' : 
                  'text-blue-600'
                }`}>
                  {message}
                </p>
              </div>
            </div>

            {/* Manual Download Fallback */}
            {status === 'completed' && downloadUrl && (
              <div className="mt-4 pt-4 border-t border-green-200">
                <a
                  href={downloadUrl}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                  Download .zip File Manually
                </a>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}