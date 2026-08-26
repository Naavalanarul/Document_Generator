const fs = require('fs');
let code = fs.readFileSync('src/DocGenApp.jsx', 'utf8');

// 1. handleFilePick & button
code = code.replace(
  /const handleFilePick = \(e\) => \{\s*const f = e\.target\.files\?\.\[0\];\s*if \(\!f\) return;\s*if \(f\.size > MAX_FILE_SIZE\) \{ alert\('File too large\. Maximum size is 50MB\.'\); return; \}\s*onFileChange\(f\);\s*\};/,
  `const handleFilePick = async (e) => {
    if (window.electronAPI) {
      const res = await window.electronAPI.openFileDialog();
      if (!res) return;
      if (res.fileSize > MAX_FILE_SIZE) { alert('File too large. Maximum size is 50MB.'); return; }
      const buffer = await window.electronAPI.readFileBuffer(res.filePath);
      onFileChange({ name: res.fileName, buffer });
    } else {
      const f = e?.target?.files?.[0];
      if (!f) return;
      if (f.size > MAX_FILE_SIZE) { alert('File too large. Maximum size is 50MB.'); return; }
      onFileChange(f);
    }
  };`
);

// 2. Click handler in Composer
code = code.replace(
  /onClick=\{\(\) => fileRef\.current\?\.click\(\)\}/,
  `onClick={() => window.electronAPI ? handleFilePick() : fileRef.current?.click()}`
);

// 3. handleDownload
code = code.replace(
  /const handleDownload = async \(downloadUrl, filename\) => \{[\s\S]*?console\.error\('Download error:', err\);\n    \}\n  \};/,
  `const handleDownload = async (downloadUrl, filename) => {
    try {
      const res = await fetch(\`\${API_BASE}\${downloadUrl}\`);
      if (!res.ok) throw new Error('Download failed');
      const arrayBuffer = await res.arrayBuffer();
      
      if (window.electronAPI) {
        await window.electronAPI.saveFile({ defaultName: filename || 'document', buffer: arrayBuffer });
      } else {
        const blob = new Blob([arrayBuffer]);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'document';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Download error:', err);
    }
  };`
);

// 4. external link
code = code.replace(
  /<a href="https:\/\/ollama\.com" target="_blank" rel="noopener noreferrer"/,
  `<a href="https://ollama.com" onClick={(e) => {
    if (window.electronAPI) {
      e.preventDefault();
      window.electronAPI.openExternal("https://ollama.com");
    }
  }} target="_blank" rel="noopener noreferrer"`
);

// 5. Cmd+N listener in App
code = code.replace(
  /useEffect\(\(\) => \{ saveToStorage\('docgen_params', params\); \}, \[params\]\);/,
  `useEffect(() => { saveToStorage('docgen_params', params); }, [params]);

  useEffect(() => {
    if (window.electronAPI) {
      return window.electronAPI.onNewSession(() => {
        handleNewSession();
      });
    }
  }, []);`
);

// 6. fd.append file
code = code.replace(
  /fd\.append\('file', file\);/,
  `if (file.buffer) {
          fd.append('file', new Blob([file.buffer]), file.name);
        } else {
          fd.append('file', file);
        }`
);

// 7. Drag region on Sidebar
code = code.replace(
  /<aside style=\{\{/,
  `<aside style={{ WebkitAppRegion: 'drag', `
);

// Make all explicit buttons no-drag so they stay clickable
code = code.replace(
  /<button /g,
  `<button style={{ WebkitAppRegion: 'no-drag' }} `
);

// Fix previously styled buttons to merge style
code = code.replace(
  /style=\{\{ WebkitAppRegion: 'no-drag' \}\} style=\{\{/g,
  `style={{ WebkitAppRegion: 'no-drag', `
);

fs.writeFileSync('src/DocGenApp.jsx', code);
console.log('Patched DocGenApp.jsx successfully.');
