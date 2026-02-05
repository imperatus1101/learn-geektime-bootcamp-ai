/**
 * Export suggestion modal component
 */

import React, { useEffect, useState } from "react";
import { Modal, Button, Space, Radio, message } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { ExportService, ExportSuggestion as ExportSuggestionType } from "../services/exportService";

interface Props {
  visible: boolean;
  onClose: () => void;
  dbName: string;
  sql: string;
  columns: Array<{ name: string; dataType: string }>;
  rows: Array<Record<string, any>>;
  rowCount: number;
}

export const ExportSuggestionModal: React.FC<Props> = ({
  visible,
  onClose,
  dbName,
  sql,
  columns,
  rows,
  rowCount,
}) => {
  const [suggestion, setSuggestion] = useState<ExportSuggestionType | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>("csv");
  const [exporting, setExporting] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (visible) {
      loadSuggestion();
    }
  }, [visible, sql, rowCount]);

  const loadSuggestion = async () => {
    setLoading(true);
    try {
      const result = await ExportService.getExportSuggestion(
        dbName,
        sql,
        columns,
        rowCount
      );
      setSuggestion(result);
      setSelectedFormat(result.suggestedFormat);
    } catch (error) {
      console.error("Failed to get export suggestion:", error);
      message.error("获取导出建议失败");
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await ExportService.exportServerSide(
        columns,
        rows,
        selectedFormat as any,
        dbName
      );
      message.success(`成功导出 ${rowCount.toLocaleString()} 行数据为 ${selectedFormat.toUpperCase()}`);
      onClose();
    } catch (error) {
      message.error("导出失败");
    } finally {
      setExporting(false);
    }
  };

  if (!suggestion || loading) {
    return (
      <Modal
        open={visible}
        onCancel={onClose}
        footer={null}
        title="导出查询结果"
      >
        <div style={{ textAlign: "center", padding: "20px" }}>
          加载中...
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      open={visible}
      onCancel={onClose}
      title={
        <Space>
          <DownloadOutlined />
          <span>导出查询结果</span>
        </Space>
      }
      footer={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleExport} loading={exporting}>
            导出
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        <div>
          <p>{suggestion.promptText}</p>
          {suggestion.reason && (
            <p style={{ color: "#666", fontSize: 13 }}>
              {suggestion.reason}
            </p>
          )}
        </div>

        <Radio.Group
          value={selectedFormat}
          onChange={(e) => setSelectedFormat(e.target.value)}
        >
          <Space direction="vertical">
            <Radio value="csv">CSV - 通用表格格式</Radio>
            <Radio value="json">JSON - 程序可读格式</Radio>
            <Radio value="excel">Excel - 数据分析格式 (.xlsx)</Radio>
            <Radio value="sql">SQL - INSERT 语句</Radio>
          </Space>
        </Radio.Group>

        <div style={{ fontSize: 12, color: "#999" }}>
          将导出 {rowCount.toLocaleString()} 行数据
        </div>
      </Space>
    </Modal>
  );
};
