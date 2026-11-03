/**
 * IndiaMart Lead Autoclick Pro - CSV & Data Management
 * Supports UTF-8 and UTF-16, Excel (.xlsx/.xls) detection, robust parsing, and export
 */

export class CSVManager {
  /**
   * Check if uploaded file is accidentally an Excel binary file (.xlsx or .xls)
   */
  static isExcelFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    return ext === 'xlsx' || ext === 'xls';
  }

  /**
   * Read file with automatic encoding fallback (UTF-8, UTF-16LE, UTF-16BE)
   */
  static async readFileText(file) {
    if (this.isExcelFile(file)) {
      throw new Error(
        `Selected file "${file.name}" is an Excel workbook (.xlsx/.xls).\n` +
        `Please open it in Excel, click "Save As", and choose "CSV UTF-8 (Comma delimited) (*.csv)" before importing.`
      );
    }

    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target.result;
        // Check for UTF-16 or binary weirdness
        if (text.includes('\u0000')) {
          // Retry as UTF-16
          const reader16 = new FileReader();
          reader16.onload = (e16) => resolve(e16.target.result);
          reader16.onerror = () => reject(new Error('Failed to read file encoding.'));
          reader16.readAsText(file, 'utf-16');
        } else {
          resolve(text);
        }
      };
      reader.onerror = () => reject(new Error('Failed to read CSV file.'));
      reader.readAsText(file, 'utf-8');
    });
  }

  /**
   * Parse CSV content into array of rows (handling quotes and commas)
   */
  static parseCSV(text) {
    const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
    const rows = [];

    for (const line of lines) {
      const row = [];
      let inQuotes = false;
      let currentField = '';

      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        const nextChar = line[i + 1];

        if (char === '"') {
          if (inQuotes && nextChar === '"') {
            currentField += '"';
            i++; // skip escaped quote
          } else {
            inQuotes = !inQuotes;
          }
        } else if (char === ',' && !inQuotes) {
          row.push(currentField.trim());
          currentField = '';
        } else {
          currentField += char;
        }
      }
      row.push(currentField.trim());
      rows.push(row);
    }

    return rows;
  }

  /**
   * Parse Keywords CSV:
   * Format: keyword,qty,unit,category,clicks,min_order_value,target_location
   */
  static parseKeywordsCSV(text) {
    const rows = this.parseCSV(text);
    if (rows.length === 0) return [];

    // Check if first row is header
    let startIndex = 0;
    const header = rows[0].map(h => h.toLowerCase());
    if (header.includes('keyword')) {
      startIndex = 1;
    }

    const keywords = [];
    for (let i = startIndex; i < rows.length; i++) {
      const row = rows[i];
      const keyword = (row[0] || '').trim();
      if (!keyword) continue;

      keywords.push({
        id: 'kw-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5),
        keyword: keyword,
        minQty: parseFloat(row[1]) || 1,
        unit: (row[2] || 'Piece').trim(),
        category: (row[3] || '').trim(),
        dailyLimit: parseInt(row[4], 10) || 0,
        minOrderValue: parseFloat(row[5]) || 0,
        targetLocation: (row[6] || '').trim(),
        clicksToday: 0
      });
    }

    return keywords;
  }

  /**
   * Parse single-column list (locations, countries, categories, blocked_locations)
   */
  static parseSingleColumnCSV(text, headerName = '') {
    const rows = this.parseCSV(text);
    if (rows.length === 0) return [];

    let startIndex = 0;
    const firstCell = (rows[0][0] || '').toLowerCase();
    if (headerName && firstCell.includes(headerName.toLowerCase())) {
      startIndex = 1;
    }

    const list = [];
    for (let i = startIndex; i < rows.length; i++) {
      const val = (rows[i][0] || '').trim();
      if (val && !list.includes(val)) {
        list.push(val);
      }
    }
    return list;
  }

  /**
   * Export array to CSV download
   */
  static exportToCSV(filename, csvContent) {
    const blob = new Blob([new Uint8Array([0xEF, 0xBB, 0xBF]), csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}

