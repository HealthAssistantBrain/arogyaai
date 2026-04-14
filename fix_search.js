const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, 'apps/frontend/src');

function getAllFiles(dirPath, arrayOfFiles) {
    const files = fs.readdirSync(dirPath);
    arrayOfFiles = arrayOfFiles || [];

    files.forEach(function (file) {
        if (fs.statSync(dirPath + "/" + file).isDirectory()) {
            arrayOfFiles = getAllFiles(dirPath + "/" + file, arrayOfFiles);
        } else {
            const ext = path.extname(file);
            if (ext === '.jsx' || ext === '.tsx') {
                arrayOfFiles.push(path.join(dirPath, "/", file));
            }
        }
    });
    return arrayOfFiles;
}

const files = getAllFiles(srcDir).filter(f => !f.includes('CommandPalette') && !f.includes('Dashboard.jsx'));

let modifiedCount = 0;

for (let file of files) {
    file = path.resolve(file); // Ensure correct path separator
    let content = fs.readFileSync(file, 'utf8');

    if (content.includes('<Search ') || content.includes('<Search\n') || content.includes('<SearchIcon ') || content.includes('<SearchX')) {
        if (content.includes('openCommandPalette')) continue;

        // Determine relative path to components/CommandPalette
        const relToSrc = path.relative(srcDir, file);
        const fileDepth = relToSrc.split(path.sep).length;

        let importPath = '';
        const isLayoutDir = relToSrc.includes(path.join('components', 'layout')) || relToSrc.includes('components/layout');

        if (isLayoutDir) {
            importPath = '../CommandPalette';
        } else if (fileDepth === 2) {
            importPath = '../components/CommandPalette'; // eg pages/Something.jsx
        } else if (fileDepth === 1) {
            importPath = './components/CommandPalette'; // eg App.jsx
        } else if (fileDepth === 3) {
            importPath = '../../components/CommandPalette';
        }

        const importStmt = `import { openCommandPalette } from '${importPath}';\n`;

        // insert import
        const lines = content.split('\n');
        let lastImportIdx = -1;
        for (let i = 0; i < lines.length; i++) {
            if (lines[i].startsWith('import ')) {
                lastImportIdx = i;
            }
        }

        if (lastImportIdx !== -1) {
            lines.splice(lastImportIdx + 1, 0, importStmt.trim());
        } else {
            lines.unshift(importStmt.trim());
        }

        content = lines.join('\n');

        // Add onClick and pointer events
        const appendStr = ` onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} `;

        content = content.replace(/<Search /g, `<Search${appendStr}`);
        content = content.replace(/<Search\n/g, `<Search${appendStr}\n`);
        content = content.replace(/<SearchIcon /g, `<SearchIcon${appendStr}`);
        content = content.replace(/<SearchX /g, `<SearchX${appendStr}`);

        fs.writeFileSync(file, content, 'utf8');
        modifiedCount++;
        console.log(`Updated ${file}`);
    }
}

console.log(`Modified ${modifiedCount} files.`);
