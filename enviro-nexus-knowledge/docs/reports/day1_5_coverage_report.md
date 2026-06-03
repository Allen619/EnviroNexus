# Day 1.5 数据覆盖与人工复核报告

## 报告边界

本报告记录 Day 1.5 使用 `files/poc-files` 下 5 份 markdown 人工整理 MethodCard 的覆盖情况。当前未读取、未解析、未比对 PDF；所有条目均保留 `needs_pdf_check=true`，后续数据治理阶段需要按原始 PDF 逐项复核。

## HJ 1147-2020

```text
standard_code: HJ 1147-2020
card_id: water_ph_hj1147_2020
markdown_source: files/poc-files/水质 pH的测定 电极法 HJ 1147-2020.md
covered_sections: 1 适用范围; 3 方法原理; 4 干扰和消除; 6 仪器和设备; 7 样品; 8 分析步骤; 9 结果表示; 11 质量保证和质量控制
method_card_fields_filled: identity; applicability; measurement; requirements; qa_qc; answer_template; evidence_refs
manual_summary_notes: 将原文中较长的校准和样品测定步骤压缩为回答所需摘要。
needs_pdf_check: true
review_status: draft_manual_review
```

## HJ 1182-2021

```text
standard_code: HJ 1182-2021
card_id: water_colority_hj1182_2021
markdown_source: files/poc-files/水质 色度的测定 稀释倍数法 HJ 1182-2021.md
covered_sections: 1 适用范围; 4 方法原理; 6 人员、环境和设备; 7 样品; 7.1 样品采集和保存; 7.2 试样的制备; 7.3 颜色描述; 8.1 初级稀释; 8.2 自然倍数稀释; 8.3 目视比色; 9 结果计算与表示; 11 质量保证和质量控制
method_card_fields_filled: identity; applicability; measurement; requirements; qa_qc; answer_template; evidence_refs
manual_summary_notes: 结果计算与表示来自 markdown 图片识别文字，需后续与 PDF 原文核对公式排版。
needs_pdf_check: true
review_status: draft_manual_review
```

## HJ 1445-2026

```text
standard_code: HJ 1445-2026
card_id: water_permanganate_index_hj1445_2026
markdown_source: files/poc-files/HJ 1445-2026 水质 高锰酸盐指数的测定 草酸钠还原酸性滴定法.md
covered_sections: 警告; 1 适用范围; 3 术语和定义; 4 方法原理; 5 干扰和消除; 7 仪器和设备; 8 样品; 9 分析步骤; 10 结果计算与表示; 12 质量保证和质量控制
method_card_fields_filled: identity; applicability; measurement; requirements; qa_qc; answer_template; evidence_refs
manual_summary_notes: 标准公式内容只保留回答摘要，未完整转录公式细节。
needs_pdf_check: true
review_status: draft_manual_review
```

## HJ 1287-2023

```text
standard_code: HJ 1287-2023
card_id: gas_smoke_blackness_hj1287_2023
markdown_source: files/poc-files/HJ 1287-2023 固定污染源废气 烟气黑度的测定 林格曼望远镜法.md
covered_sections: 1 适用范围; 4 方法原理; 5 仪器和设备; 6.1 观测位置和条件; 6.2 观测步骤; 7 现场观测记录; 8 结果计算与表示; 10 质量保证和质量控制; 11 注意事项; 附录 B
method_card_fields_filled: identity; applicability; measurement; requirements; qa_qc; answer_template; evidence_refs
manual_summary_notes: 现场观测记录和表格内容仅提取关键字段要求。
needs_pdf_check: true
review_status: draft_manual_review
```

## HJ 1332-2023

```text
standard_code: HJ 1332-2023
card_id: gas_thc_methane_nmhc_hj1332_2023
markdown_source: files/poc-files/HJ 1332-2023 固定污染源废气 总烃、甲烷和非甲烷总烃的测定 便携式气相色谱-氢火焰离子化检测器法.md
covered_sections: 1 适用范围; 4 方法原理; 5 干扰和消除; 7 仪器和设备; 8 样品; 9 分析步骤; 10 结果计算与表示; 12 质量保证和质量控制; 13 注意事项
method_card_fields_filled: identity; applicability; measurement; requirements; qa_qc; answer_template; evidence_refs
manual_summary_notes: 非甲烷总烃计算公式没有完整进入 MethodCard，仅保留“总烃和甲烷之差”的回答摘要。
needs_pdf_check: true
review_status: draft_manual_review
```
