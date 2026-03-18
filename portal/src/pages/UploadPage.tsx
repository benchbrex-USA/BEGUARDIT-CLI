// Upload page — upload JSON canonical assessment report (§10.1)
import { useState, useRef, type DragEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadAssessment } from '../api/queries';
import { useUiStore } from '../stores/uiStore';
import { Button, Card } from '../components/ui';

export default function UploadPage() {
  const navigate = useNavigate();
  const addToast = useUiStore((s) => s.addToast);
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFile = (f: File | undefined) => {
    if (!f) return;
    if (!f.name.endsWith('.json')) {
      setError('Please upload a .json file (canonical report format).');
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError('File exceeds 50 MB limit.');
      return;
    }
    setError('');
    setFile(f);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    handleFile(e.target.files?.[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    try {
      const result = await uploadAssessment(file);
      addToast({
        type: 'success',
        message: `Imported ${result.findings_imported} findings, ${result.assets_imported} assets, ${result.evidence_imported} evidence items.`,
        duration: 8000,
      });
      navigate(`/assessments/${result.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-xl font-bold mb-4">Upload Assessment</h1>
      <p className="text-sm text-slate-500 mb-6">
        Upload a JSON canonical report file produced by <code className="bg-slate-100 px-1 rounded text-xs">beguardit start --mode online</code>.
        The file will be validated and imported into the system.
      </p>

      <Card>
        {/* Drop zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            dragging
              ? 'border-blue-400 bg-blue-50'
              : file
                ? 'border-green-400 bg-green-50'
                : 'border-slate-300 hover:border-slate-400'
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleChange}
          />

          {file ? (
            <div>
              <p className="text-sm font-medium text-green-700">{file.name}</p>
              <p className="text-xs text-slate-500 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-slate-600">Drop a JSON file here or click to browse</p>
              <p className="text-xs text-slate-400 mt-1">Max 50 MB, .json format</p>
            </div>
          )}
        </div>

        {error && <p className="text-sm text-red-600 mt-3">{error}</p>}

        <div className="flex gap-2 mt-4">
          <Button loading={loading} disabled={!file} onClick={handleUpload}>
            Upload & Import
          </Button>
          {file && (
            <Button variant="ghost" onClick={() => { setFile(null); setError(''); }}>
              Clear
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
