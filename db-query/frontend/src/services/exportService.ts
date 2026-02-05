/**
 * Export service - unified export functionality for frontend
 */

import { apiClient } from "./api";

export interface ExportOptions {
  format: "csv" | "json" | "excel" | "sql";
  delimiter?: string;
  includeHeaders?: boolean;
  prettyPrint?: boolean;
  sheetName?: string;
  tableName?: string;
}

export interface ExportSuggestion {
  shouldSuggest: boolean;
  suggestedFormat: string;
  reason: string;
  promptText: string;
}

export interface ExportHistoryEntry {
  id: number;
  databaseName: string;
  sql: string;
  exportFormat: string;
  fileName: string;
  fileSizeBytes: number;
  rowCount: number;
  exportTimeMs: number;
  createdAt: string;
}

export class ExportService {
  /**
   * Export query result (client-side) - for backward compatibility
   */
  static exportClientSide(
    columns: Array<{ name: string; dataType: string }>,
    rows: Array<Record<string, any>>,
    format: "csv" | "json",
    dbName: string
  ) {
    if (format === "csv") {
      this.exportToCSV(columns, rows, dbName);
    } else if (format === "json") {
      this.exportToJSON(rows, dbName);
    }
  }

  /**
   * Export query result (server-side) - new implementation
   */
  static async exportServerSide(
    columns: Array<{ name: string; dataType: string }>,
    rows: Array<Record<string, any>>,
    format: "csv" | "json" | "excel" | "sql",
    dbName: string,
    options?: Partial<ExportOptions>
  ): Promise<void> {
    try {
      const response = await apiClient.post(
        `/api/v1/dbs/${dbName}/export`,
        {
          columns,
          rows,
          format,
          options: {
            delimiter: ",",
            includeHeaders: true,
            prettyPrint: true,
            ...options,
          },
        },
        {
          responseType: "blob",
        }
      );

      // Get filename from response headers
      const contentDisposition = response.headers["content-disposition"];
      const fileNameMatch = contentDisposition?.match(/filename="(.+)"/);
      const fileName = fileNameMatch ? fileNameMatch[1] : `export.${format}`;

      // Trigger download
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Export failed:", error);
      throw error;
    }
  }

  /**
   * Query and export in one operation
   */
  static async queryAndExport(
    dbName: string,
    sql: string,
    format: "csv" | "json" | "excel" | "sql",
    options?: Partial<ExportOptions>
  ): Promise<void> {
    try {
      const response = await apiClient.post(
        `/api/v1/dbs/${dbName}/query-and-export`,
        {
          sql,
          format,
          options: {
            delimiter: ",",
            includeHeaders: true,
            ...options,
          },
        },
        {
          responseType: "blob",
        }
      );

      // Trigger download
      const contentDisposition = response.headers["content-disposition"];
      const fileNameMatch = contentDisposition?.match(/filename="(.+)"/);
      const fileName = fileNameMatch ? fileNameMatch[1] : `export.${format}`;

      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Query and export failed:", error);
      throw error;
    }
  }

  /**
   * Get export suggestion from server
   */
  static async getExportSuggestion(
    dbName: string,
    sql: string,
    columns: Array<{ name: string; dataType: string }>,
    rowCount: number
  ): Promise<ExportSuggestion> {
    const response = await apiClient.post(
      `/api/v1/dbs/${dbName}/export/suggest`,
      {
        sql,
        columns,
        rowCount,
      }
    );
    return response.data;
  }

  /**
   * Parse natural language export command
   */
  static async parseNLCommand(input: string): Promise<any> {
    const response = await apiClient.post("/api/v1/dbs/export/parse-nl", {
      input,
    });
    return response.data;
  }

  /**
   * Get export history
   */
  static async getExportHistory(
    dbName: string,
    limit: number = 10
  ): Promise<ExportHistoryEntry[]> {
    const response = await apiClient.get(`/api/v1/dbs/${dbName}/exports`, {
      params: { limit },
    });
    return response.data;
  }

  // Private methods: client-side export implementations
  private static exportToCSV(
    columns: Array<{ name: string; dataType: string }>,
    rows: Array<Record<string, any>>,
    dbName: string
  ) {
    const headers = columns.map((col) => col.name);
    const csvRows = [headers.join(",")];

    rows.forEach((row) => {
      const values = headers.map((header) => {
        const value = row[header];
        if (value === null || value === undefined) return "";
        const stringValue = String(value);
        // RFC 4180: escape quotes and wrap in quotes if contains comma, quote, or newline
        if (
          stringValue.includes(",") ||
          stringValue.includes('"') ||
          stringValue.includes("\n")
        ) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      });
      csvRows.push(values.join(","));
    });

    const csvContent = csvRows.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5);
    link.href = URL.createObjectURL(blob);
    link.download = `${dbName}_${timestamp}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  private static exportToJSON(rows: Array<Record<string, any>>, dbName: string) {
    const jsonContent = JSON.stringify(rows, null, 2);
    const blob = new Blob([jsonContent], {
      type: "application/json;charset=utf-8;",
    });
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5);
    link.href = URL.createObjectURL(blob);
    link.download = `${dbName}_${timestamp}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  }
}
