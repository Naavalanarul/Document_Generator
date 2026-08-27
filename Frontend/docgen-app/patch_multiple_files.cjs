const fs = require('fs');
let code = fs.readFileSync('src/DocGenApp.jsx', 'utf8');

// 1. App state
code = code.replace(
  /const \[file, setFile\] = useState\(null\);\n  const \[uploadedFilePath, setUploadedFilePath\] = useState\(''\);/,
  `const [files, setFiles] = useState([]);\n  const [uploadedFilePaths, setUploadedFilePaths] = useState([]);`
);

// 2. Composer props
code = code.replace(
  /function Composer\(\{ sourceType, onSourceTypeChange, file, onFileChange, url, onUrlChange, searchQuery, onSearchQueryChange,/,
  `function Composer({ sourceType, onSourceTypeChange, files, onFilesChange, url, onUrlChange, searchQuery, onSearchQueryChange,`
);

// 3. Composer rendering
code = code.replace(
  /<Composer\n\s*sourceType=\{sourceType\} onSourceTypeChange=\{setSourceType\}\n\s*file=\{file\} onFileChange=\{f => \{ setFile\(f\); setUploadedFilePath\(''\); \}\}/,
  `<Composer\n            sourceType={sourceType} onSourceTypeChange={setSourceType}\n            files={files} onFilesChange={f => { setFiles(f); setUploadedFilePaths([]); }}`
);

// 4. handleNewSession
code = code.replace(
  /setFile\(null\);\n    setUploadedFilePath\(''\);/,
  `setFiles([]);\n    setUploadedFilePaths([]);`
);

// 5. handleFilePick
code = code.replace(
  /const handleFilePick = async \(e\) => \{[\s\S]*?onFileChange\(f\);\n    \}\n  \};/,
  `const handleFilePick = async (e) => {
    if (window.electronAPI) {
      const res = await window.electronAPI.openFileDialog();
      if (!res) return;
      
      const newFiles = [...(files || [])];
      for (const f of res) {
        if (f.fileSize > MAX_FILE_SIZE) { alert(\`File \${f.fileName} too large.\`); continue; }
        const buffer = await window.electronAPI.readFileBuffer(f.filePath);
        newFiles.push({ name: f.fileName, buffer });
      }
      onFilesChange(newFiles.slice(0, 20));
    } else {
      const selected = Array.from(e.target.files || []);
      if (!selected.length) return;
      const valid = selected.filter(f => f.size <= MAX_FILE_SIZE);
      if (valid.length < selected.length) alert('Some files were too large and skipped.');
      onFilesChange([...(files || []), ...valid].slice(0, 20));
    }
  };`
);

// 6. Composer UI for file
const fileUiRegex = /\{sourceType === 'file' && \(\s*<div style=\{\{ marginBottom: 12 \}\}>\s*\{file \? \([\s\S]*?\}\s*<input ref=\{fileRef\} type="file" accept="\.pdf,\.docx,\.pptx,\.txt,\.md,\.csv" onChange=\{handleFilePick\} style=\{\{ display: 'none' \}\} aria-hidden="true" \/>\s*<\/div>\s*\)\}/;

const newFileUi = `{sourceType === 'file' && (
          <div style={{ marginBottom: 12 }}>
            {files && files.length > 0 ? (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {files.map((f, i) => (
                  <div key={i} style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 12px',
                    background: 'var(--color-surface)', borderRadius: 'var(--radius-input)', fontSize: 13, color: 'var(--color-text-primary)',
                  }}>
                    {Icons.file}
                    <span style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                    <button onClick={() => onFilesChange(files.filter((_, idx) => idx !== i))} aria-label="Remove file"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)', padding: 0, display: 'flex' }}>
                      {Icons.x}
                    </button>
                  </div>
                ))}
                {files.length < 20 && (
                   <button onClick={() => window.electronAPI ? handleFilePick() : fileRef.current?.click()}
                    style={{ padding: '6px 12px', border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-input)', background: 'transparent', color: 'var(--color-text-muted)', fontSize: 13, cursor: 'pointer' }}>
                    + Add More
                   </button>
                )}
              </div>
            ) : (
              <button onClick={() => window.electronAPI ? handleFilePick() : fileRef.current?.click()}
                style={{
                  padding: '8px 14px', border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-input)',
                  background: 'transparent', color: 'var(--color-text-muted)', fontSize: 13, cursor: 'pointer',
                  transition: 'border-color 200ms',
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--color-accent)'}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--color-border)'}>
                Choose files (up to 20, max 50MB each)
              </button>
            )}
            <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.pptx,.txt,.md,.csv" onChange={handleFilePick} style={{ display: 'none' }} aria-hidden="true" />
          </div>
        )}`;

code = code.replace(fileUiRegex, newFileUi);

// 7. Generate Upload logic
const generateUploadRegex = /\/\/ Upload if needed\s*let fp = uploadedFilePath;\s*if \(sourceType === 'file' && file && !uploadedFilePath\) \{[\s\S]*?setUploadedFilePath\(fp\);\s*\}/;

const newGenerateUpload = `// Upload if needed
      let fp = uploadedFilePaths;
      if (sourceType === 'file' && files.length > 0 && uploadedFilePaths.length === 0) {
        const fd = new FormData();
        for (const f of files) {
          if (f.buffer) {
            fd.append('files', new Blob([f.buffer]), f.name);
          } else {
            fd.append('files', f);
          }
        }
        const r = await fetch(\`\${API_BASE}/upload\`, { method: 'POST', body: fd, signal: ac.signal });
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'File upload failed'); }
        const resJson = await r.json();
        fp = resJson.file_paths || [];
        setUploadedFilePaths(fp);
      }`;

code = code.replace(generateUploadRegex, newGenerateUpload);

// 8. Generate form append
code = code.replace(
  /if \(sourceType === 'file' && fp\) fd\.append\('file_path', fp\);/,
  `if (sourceType === 'file' && fp.length > 0) fd.append('file_paths', fp.join(','));`
);

fs.writeFileSync('src/DocGenApp.jsx', code);
console.log('Patched DocGenApp.jsx for multiple files');
