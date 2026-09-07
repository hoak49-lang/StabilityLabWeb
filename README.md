# StabilityLab Web

Vietnamese drug stability analysis workspace. The existing StabilityLab statistical engine runs in a dedicated browser worker using Pyodide 314.0.6. No uploaded study data are sent to an application server. The runtime and NumPy/SciPy are downloaded from the pinned jsDelivr Pyodide distribution. Openpyxl 3.1.5 and et-xmlfile 2.0.0 are packaged locally with their license metadata.

Import CSV/XLSX, map columns, set specifications, review extrapolation conditions, calculate fixed-batch regressions and confidence bounds, inspect diagnostics, and export HTML/XLSX/JSON. Project files can be saved and reopened. Session data and history are volatile: download reports and projects before refreshing or closing the page.

This implements selected quantitative ICH Q1E methods. It is not an ICH certification, a validated GxP system, or a replacement for scientific review. It does not implement regulated audit trails or electronic signatures. SHA-256 checks detect accidental record changes within the workflow; they do not provide tamper-proof provenance.

Development: pnpm install; pnpm dev. Validation: pnpm test. Production static build: pnpm build.

The statistical engine is retained from the Windows application. The browser adapter reuses its request handlers without starting an HTTP server. Scientific runtime versions differ from the Windows package and are independently checked by test.mjs against its reference calculation.

Runtime documentation: https://pyodide.org/en/stable/usage/index.html

## Study design
Version 1.1 adds full factorial scheduling, user-selected bracketing extremes, time-point matrixing, and combined designs. Each storage condition is scheduled independently. Initial/final, 12-month long-term and specified interim-submission checkpoints are protected. Early observation counts are checked and repaired conservatively. Actual reductions and unequal row counts are shown. Reduced designs remain drafts; the software does not establish power or multi-factor shelf life.

Export a draft protocol, schedule, planned observation template and bracketed-combination list to Excel. Save/reopen the design as JSON. Analysis imports strength and pack columns and requires selecting one combination; no cross-strength/pack pooling occurs.

WebMCP hooks are feature-detected. A supported live modelContext validation surface was not available; those optional hooks have not been integration-verified.
