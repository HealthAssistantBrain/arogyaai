const fs = require('fs');
const path = require('path');

const pagesDir = path.join(__dirname, 'apps/frontend/src/pages');

function walk(dir) {
    let results = [];
    const list = fs.readdirSync(dir);
    list.forEach(file => {
        file = path.join(dir, file);
        const stat = fs.statSync(file);
        if (stat && stat.isDirectory()) {
            results = results.concat(walk(file));
        } else if (file.endsWith('.jsx')) {
            results.push(file);
        }
    });
    return results;
}

const files = walk(pagesDir);
let modifiedCount = 0;

// To remove the "Dr. Sarah Chen" / "Alex Johnson" chunks inside the headers.
// Specifically targeting the flex wrapper that contains the profile and is often the right-most child inside the header.
const regex1 = /<div className="[^"]*?flex[^"]*items-center[^"]*">\s*<div className="text-right[^>]*?>[\s\S]*?(Alex Johnson|Dr\. Sarah Chen|Alex Rivera)[\s\S]*?<\/div>\s*(<img[^>]*?>|<div[^>]*?>\s*<img[^>]*?>\s*<\/div>)\s*<\/div>/g;

files.forEach(file => {
    let content = fs.readFileSync(file, 'utf8');
    let original = content;

    // Replace the profile badges
    content = content.replace(regex1, '');

    // And the new UserProfileBadge that was previously injected
    content = content.replace(/<div className="hidden lg:block fixed left-6 bottom-6 z-30">\s*<UserProfileBadge[\s\S]*?\/>\s*<\/div>/g, '');
    content = content.replace(/import UserProfileBadge from '[\.\/]+components\/UserProfileBadge';\s*/g, '');

    if (original !== content) {
        fs.writeFileSync(file, content, 'utf8');
        modifiedCount++;
        console.log('Modified:', path.basename(file));
    }
});

console.log(`Processed ${files.length} files. Modified ${modifiedCount} files.`);
