// Adds a "Show data" button to every editable Pyodide block.
//
// The button floats the first rows of the dataframe a block works with over
// the right of the code. Setup data is available before the first run, so
// participants can read the column names while filling in blanks. Names
// created by the exercise become available after running it.
//
// By default the frame is inferred from the block's last statement. The data
// argument of a `ggplot()` or `GT()` call wins, then the value of the last
// expression or assignment. Set `#| preview: <python expression>` on the block
// to choose a frame, `#| preview: [frame1, frame2]` to offer a choice, or
// `#| preview: false` to hide the button.
//
// Relies on internals of the vendored quarto-live runtime
// (`window._exercise_ojs_runtime` and the OJS cell `pyodideOjs`), so re-check
// it after updating the extension.

(() => {
  const N_ROWS = 10;

  // Runs in a scratch namespace so the helpers stay out of the participant's
  // environment, which is passed in as `_environment` (None before the first
  // run).
  const PREVIEW_PYTHON = `
import ast

_DATA_CALLS = ("ggplot", "GT")


def _data_node(statement):
    value = getattr(statement, "value", None)
    if value is None:
        return None
    for node in ast.walk(value):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", getattr(node.func, "attr", None))
        if name not in _DATA_CALLS:
            continue
        if node.args:
            return node.args[0]
        for keyword in node.keywords:
            if keyword.arg == "data":
                return keyword.value
    return value


def _evaluate(node, namespace):
    value = eval(compile(ast.Expression(node), "<preview>", "eval"), namespace)
    return value, ast.unparse(node)


def _last_value(body, namespace):
    last = body[-1] if body else None
    if not isinstance(last, (ast.Expr, ast.Assign)):
        return None, ""
    node = _data_node(last)
    if node is last.value and isinstance(last, ast.Assign):
        target = last.targets[0]
        if isinstance(target, ast.Name) and target.id in namespace:
            return namespace[target.id], target.id
    return _evaluate(node, namespace)


def _namespace(setup, environment):
    namespace = {}
    if setup:
        exec(setup, namespace)
    if environment is not None:
        namespace.update(environment)
    return namespace


def _run(body, namespace):
    exec(compile(ast.Module(body, []), "<preview>", "exec"), namespace)


def _resolve(expr, namespace, code):
    if expr:
        return eval(expr, namespace), expr
    body = ast.parse(code).body
    try:
        return _last_value(body, namespace)
    except NameError:
        # The data may be defined by the block's own earlier lines.
        try:
            _run(body[:-1], namespace)
        except (ImportError, NameError, TypeError, ValueError):
            pass
        return _last_value(body, namespace)


def _preview(expr, environment, setup, code, n_rows):
    import pandas as pd
    import polars as pl

    obj, name = _resolve(expr, _namespace(setup, environment), code)
    if isinstance(obj, pd.DataFrame):
        frame = obj
    elif isinstance(getattr(obj, "data", None), pd.DataFrame):
        frame = obj.data
    elif hasattr(obj, "_tbl_data"):
        frame = obj._tbl_data
    else:
        frame = obj
    if isinstance(frame, pl.DataFrame):
        # The browser build does not support Polars' Arrow-to-pandas conversion.
        sample = pd.DataFrame(frame.head(n_rows).to_dict(as_series=False))
    else:
        if not isinstance(frame, pd.DataFrame) and hasattr(frame, "to_pandas"):
            frame = frame.to_pandas()
        if not isinstance(frame, pd.DataFrame):
            raise TypeError(
                f"Expected a dataframe, got {type(obj).__name__}. "
                "Set '#| preview: <expression>' on this block."
            )
        sample = frame.head(n_rows)
    html = sample.to_html(border=0, na_rep="")
    return {"name": name, "html": html, "rows": frame.shape[0], "cols": frame.shape[1]}


def _safe_preview(expr, environment, setup, code, n_rows, has_run):
    import json

    try:
        return json.dumps(_preview(expr, environment, setup, code, n_rows))
    except NameError as error:
        if not has_run and expr == error.name:
            message = f"Run this cell to preview {expr}."
        elif "___" in code:
            message = f"Fill in the blanks the data depends on ({error})."
        else:
            message = f"Could not find the data ({error})."
        return json.dumps({"message": message})
    except (AttributeError, ImportError, KeyError, SyntaxError, TypeError, ValueError) as error:
        return json.dumps({"message": f"Could not show the data: {error}"})


_safe_preview(_expr, _environment, _setup, _code, _n_rows, _has_run)
`;

  const decodeScript = (type) => {
    const script = document.querySelector(`script[type="${type}"]`);
    if (!script) return null;
    const { b64Decode } = window._exercise_ojs_runtime;
    return JSON.parse(b64Decode(script.textContent));
  };

  const environmentLabel = (attr) => {
    const envir = attr.envir ?? (attr.exercise ? `exercise-env-${attr.exercise}` : "global");
    return !attr.exercise || envir === "global" ? envir : `${envir}-result`;
  };

  const mainModule = () => window._ojs.ojsConnector.mainModule;

  const editorCode = (cell) =>
    [...cell.querySelectorAll(".cm-content .cm-line")].map((line) => line.textContent).join("\n");

  const renderPreview = async (cell, attr, expression, hasRun) => {
    const { PyodideEnvironment } = window._exercise_ojs_runtime;
    const { pyodidePromise } = await mainModule().value("pyodideOjs");
    const pyodide = await pyodidePromise;
    const manager = PyodideEnvironment.instance(pyodide);

    const label = environmentLabel(attr);
    const setup = attr.exercise ? decodeScript(`exercise-setup-${attr.exercise}-contents`) : null;
    const scratch = await pyodide.toPy({
      _environment: label in manager.env ? await manager.get(label) : undefined,
      _expr: typeof expression === "string" ? expression : "",
      _setup: setup?.code ?? "",
      _code: editorCode(cell),
      _n_rows: N_ROWS,
      _has_run: hasRun,
    });
    try {
      // The worker returns an opaque object instead of throwing on a Python
      // error, so anything but a string means the helper itself failed.
      const result = await pyodide.runPythonAsync(PREVIEW_PYTHON, { globals: scratch });
      return typeof result === "string" ? JSON.parse(result) : { message: "Could not show the data." };
    } finally {
      scratch.destroy();
    }
  };

  const errorText = (error) => {
    const lines = String(error.message ?? error).trim().split("\n");
    return lines[lines.length - 1];
  };

  // The buttons on the left of the editor header, created if the block has none.
  const leftButtonGroup = (card) => {
    const left = card.querySelector(".card-header > div:first-child");
    let group = left.querySelector(".btn-group");
    if (!group) {
      group = document.createElement("div");
      group.className = "btn-group btn-group-exercise-editor btn-group-sm";
      left.appendChild(group);
    }
    return group;
  };

  const addButton = (runButton) => {
    const cell = runButton.closest(".exercise-cell");
    const card = runButton.closest(".exercise-editor");
    if (!cell || !card || cell.dataset.previewReady) return;
    const block = decodeScript(`${cell.id}-contents`);
    if (!block || block.attr.preview === false) return;
    const editor = card.parentElement;
    const indicator = card.querySelector(".exercise-editor-eval-indicator");
    cell.dataset.previewReady = "true";

    const button = document.createElement("a");
    button.className = "d-flex align-items-center gap-1 btn btn-exercise-editor btn-outline-dark text-nowrap";
    button.setAttribute("role", "button");
    button.setAttribute("tabindex", "0");
    button.textContent = "Show data";
    leftButtonGroup(card).prepend(button);

    const panel = document.createElement("div");
    panel.className = "data-preview d-none";
    card.querySelector(".exercise-editor-body").appendChild(panel);

    const { preview } = block.attr;
    const expressions = Array.isArray(preview) ? preview : [preview];
    const selector = expressions.length > 1 ? document.createElement("select") : null;
    if (selector) {
      selector.className = "form-select form-select-sm";
      selector.setAttribute("aria-label", "DataFrame");
      for (const expression of expressions) {
        const option = document.createElement("option");
        option.textContent = expression;
        selector.appendChild(option);
      }
    }

    const frameName = selector ?? document.createElement("code");
    const summary = document.createElement("span");
    summary.setAttribute("role", "status");
    const shape = document.createElement("p");
    shape.className = "data-preview-shape";
    shape.append(frameName, summary);
    const output = document.createElement("div");
    panel.append(shape, output);

    let latestRequest = 0;
    const showPreview = async () => {
      const request = ++latestRequest;
      const expression = expressions[selector?.selectedIndex ?? 0];
      if (!selector) frameName.textContent = "";
      summary.textContent = "Loading…";
      output.textContent = "";
      let result;
      try {
        result = await renderPreview(cell, block.attr, expression, editor.value.code !== null);
      } catch (error) {
        result = { message: `Could not show the data: ${errorText(error)}` };
      }
      if (request !== latestRequest) return;
      if (result.message) {
        summary.textContent = result.message;
        return;
      }

      if (!selector) frameName.textContent = result.name;
      summary.textContent = `· First ${Math.min(N_ROWS, result.rows)} of ${result.rows} rows, ${result.cols} columns`;
      output.innerHTML = result.html;
    };
    selector?.addEventListener("change", showPreview);

    // Quarto Live hides this editor's indicator after updating its environment.
    new MutationObserver(() => {
      if (indicator.classList.contains("d-none") && !panel.classList.contains("d-none")) {
        showPreview();
      }
    }).observe(indicator, { attributes: true, attributeFilter: ["class"] });

    const setOpen = (open) => {
      panel.classList.toggle("d-none", !open);
      button.textContent = open ? "Hide data" : "Show data";
    };

    const toggle = () => {
      const open = panel.classList.contains("d-none");
      setOpen(open);
      if (open) showPreview();
    };
    button.onclick = toggle;
    button.onkeydown = (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggle();
      }
    };
  };

  const scan = () => {
    if (!window._exercise_ojs_runtime) return;
    document.querySelectorAll(".exercise-editor-btn-run-code").forEach(addButton);
  };

  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
