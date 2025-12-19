# Obsidian Vault Sync Guide

This guide shows you how to sync your Obsidian vault with the chat interface's documents folder for seamless testing and development.

## Quick Start

Choose one of these methods based on your needs:

### Option 1: Symbolic Link (Recommended)
**Best for**: Real-time sync, no overhead, seamless integration

```bash
# Back up current documents
mv repo_src/backend/documents repo_src/backend/documents_backup

# Create symbolic link to your entire vault
ln -s /path/to/your/obsidian/vault repo_src/backend/documents

# Or link to a specific folder within your vault
ln -s /path/to/your/obsidian/vault/project-docs repo_src/backend/documents
```

### Option 2: Incremental Sync (New! 🚀)
**Best for**: Only sync changed files, efficient updates

```bash
# Incremental sync - only copies changed/new files
pnpm obsidian:sync-incremental /path/to/your/obsidian/vault

# Incremental sync specific subfolder
pnpm obsidian:sync-incremental /path/to/your/obsidian/vault project-docs
```

### Option 3: Auto-Watch with Incremental Sync
**Best for**: Automatic updates, efficient file watching

```bash
# Watch and auto-sync only changed files (recommended)
pnpm obsidian:watch /path/to/your/obsidian/vault

# Smart watch - syncs individual files as they change
pnpm obsidian:watch-smart /path/to/your/obsidian/vault
```

### Option 4: Full Sync (Original)
**Best for**: Complete refresh, first-time setup

```bash
# Full sync - copies all files every time
pnpm obsidian:sync /path/to/your/obsidian/vault
```

## Detailed Instructions

### Finding Your Obsidian Vault Path

Common Obsidian vault locations:
- **macOS**: `~/Documents/ObsidianVault`
- **Windows**: `C:\Users\YourName\Documents\ObsidianVault`
- **Linux**: `~/Documents/ObsidianVault`

To find your vault path:
1. Open Obsidian
2. Open your vault
3. Go to Settings → About → Show vault folder
4. Copy the path shown

### Method 1: Symbolic Link Setup

**Advantages:**
- ✅ Real-time sync (changes appear immediately)
- ✅ No file copying overhead
- ✅ Single source of truth
- ✅ Works with any Obsidian plugin

**Steps:**
```bash
# 1. Back up current documents folder
mv repo_src/backend/documents repo_src/backend/documents_backup

# 2. Create symbolic link (replace with your actual path)
ln -s ~/Documents/MyObsidianVault repo_src/backend/documents

# 3. Verify the link works
ls -la repo_src/backend/documents/
```

### Method 2: Incremental Sync (Recommended for Automation)

**Advantages:**
- ✅ Only syncs changed files (super efficient!)
- ✅ Uses `rsync` for smart comparison
- ✅ Handles file deletions
- ✅ Much faster than full sync

**Usage:**
```bash
# Incremental sync using rsync
./repo_src/scripts/sync-obsidian-incremental.sh ~/Documents/MyObsidianVault

# Or via pnpm
pnpm obsidian:sync-incremental ~/Documents/MyObsidianVault
```

### Method 3: Smart Watching

**Two watching options:**

#### Option A: Incremental Watch (Recommended)
```bash
# Uses incremental sync when changes detected
pnpm obsidian:watch ~/Documents/MyObsidianVault
```

#### Option B: Smart File-Level Watch
```bash
# Syncs individual files as they change
pnpm obsidian:watch-smart ~/Documents/MyObsidianVault
```

### Method 4: Using pnpm Scripts

For convenience, use the predefined pnpm scripts:

```bash
# Get symbolic link instructions
pnpm obsidian:link

# Full sync (copies all files)
pnpm obsidian:sync /path/to/vault [subfolder]

# Incremental sync (only changed files)
pnpm obsidian:sync-incremental /path/to/vault [subfolder]

# Auto-watch with incremental sync
pnpm obsidian:watch /path/to/vault [subfolder]

# Smart watch (file-level sync)
pnpm obsidian:watch-smart /path/to/vault [subfolder]
```

## Performance Comparison

| Method | Initial Sync | Subsequent Changes | File Deletions | Overhead |
|--------|-------------|-------------------|----------------|----------|
| Symbolic Link | Instant | Instant | Instant | None |
| Incremental Sync | Medium | **Fast** | ✅ Handled | Low |
| Smart Watch | Medium | **Very Fast** | ✅ Handled | Low |
| Full Sync | Slow | Slow | ✅ Handled | High |

## Testing Your Setup

1. **Start the chat interface:**
   ```bash
   pnpm dev:clean
   ```

2. **Open the web interface:**
   Navigate to http://localhost:5173

3. **Test with a question:**
   - Try asking about content from your Obsidian notes
   - Check the "Tool" messages to see which files were selected

4. **Test the sync efficiency:**
   - Make a small change to one file in Obsidian
   - Watch the sync output - it should only mention the changed file

## Troubleshooting

### rsync Not Found
```bash
# Install on macOS
brew install rsync

# Install on Linux
sudo apt-get install rsync  # Ubuntu/Debian
sudo yum install rsync      # CentOS/RHEL
```

### Symbolic Link Issues
```bash
# Check if link is working
ls -la repo_src/backend/documents/

# If broken, recreate
rm repo_src/backend/documents
ln -s /correct/path/to/vault repo_src/backend/documents
```

### File Permissions
```bash
# Make scripts executable
chmod +x repo_src/scripts/*.sh
```

### fswatch Not Found
```bash
# Install on macOS
brew install fswatch

# Install on Linux
sudo apt-get install fswatch  # Ubuntu/Debian
sudo yum install fswatch       # CentOS/RHEL
```

## Best Practices

1. **For Development**: Use symbolic links for real-time sync
2. **For Automation**: Use incremental sync for efficiency
3. **For Large Vaults**: Use smart watch to minimize I/O
4. **Organize Your Vault**: Create dedicated folders for different projects
5. **Use Markdown**: The chat interface works best with `.md` files
6. **Test Regularly**: Verify the sync is working as expected

## What's New in This Version

- 🚀 **Incremental Sync**: Only sync changed files using `rsync`
- 🎯 **Smart Watch**: Sync individual files as they change
- ⚡ **Performance**: Much faster for large vaults
- 🗑️ **Deletion Handling**: Properly removes deleted files
- 📊 **Better Feedback**: Shows exactly which files are being synced

## Restoring Original Documents

If you need to restore the original documents folder:

```bash
# Remove symbolic link or synced folder
rm -rf repo_src/backend/documents

# Restore from backup
mv repo_src/backend/documents_backup repo_src/backend/documents
```

Happy note-taking and testing! 🧠✨ 