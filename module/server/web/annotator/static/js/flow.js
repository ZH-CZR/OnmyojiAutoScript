/* 自定义流程编辑器：标注 -> 步骤编排 -> 单步测试 -> 生成任务代码 */
(() => {
  'use strict';

  const FLOW_API = '/tool/flow/api';
  const ANNOTATOR_API = '/tool/annotator/api';

  const state = {
    ops: [],
    opMap: {},
    compareOps: [],
    varPrefix: 'var:',
    flows: [],
    flow: null,
    selectedUid: null,
    uid: 0,
    rules: [],
    tasks: [],
    pages: [],
    configs: [],
    sessionId: '',
    ws: null,
    lastStepResult: null,
  };

  const $ = (id) => document.getElementById(id);

  // ---------------------------------------------------------------- 请求
  async function request(url, options = {}) {
    const response = await fetch(url, options);
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch (error) {
      data = { detail: text };
    }
    if (!response.ok) {
      const detail = data && data.detail;
      const message = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.code)) || `HTTP ${response.status}`;
      throw new Error(message);
    }
    return data;
  }

  const apiGet = (path) => request(path);
  const apiPost = (path, body) => request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });

  // ---------------------------------------------------------------- 工具
  function setStatus(text, isError = false) {
    const el = $('flowStatus');
    el.textContent = text || '';
    el.style.color = isError ? 'var(--danger)' : 'var(--text-muted)';
  }

  function newUid() {
    state.uid += 1;
    return `u${state.uid}`;
  }

  function assignUids(steps) {
    (steps || []).forEach((step) => {
      step._uid = newUid();
      ['then', 'else', 'body'].forEach((key) => {
        if (Array.isArray(step[key])) assignUids(step[key]);
      });
    });
  }

  function renumber(steps, prefix = 's') {
    (steps || []).forEach((step, index) => {
      step.id = `${prefix}${index + 1}`;
      if (Array.isArray(step.then)) renumber(step.then, `${step.id}_`);
      if (Array.isArray(step.else)) renumber(step.else, `${step.id}_`);
      if (Array.isArray(step.body)) renumber(step.body, `${step.id}_`);
    });
  }

  function serializeSteps(steps) {
    return (steps || []).map((step) => {
      const out = {};
      Object.keys(step).forEach((key) => {
        if (key === '_uid') return;
        if (Array.isArray(step[key])) out[key] = serializeSteps(step[key]);
        else out[key] = step[key];
      });
      return out;
    });
  }

  function serializeFlow() {
    const flow = state.flow || { name: '', task: '', vars: {}, steps: [] };
    renumber(flow.steps || []);
    return {
      name: ($('flowName').value || flow.name || 'flow').trim(),
      task: (flow.task || '').trim(),
      comment: flow.comment || '',
      vars: flow.vars || {},
      steps: serializeSteps(flow.steps || []),
    };
  }

  function findNode(uid, steps = (state.flow && state.flow.steps) || [], parent = null) {
    for (let index = 0; index < steps.length; index += 1) {
      const step = steps[index];
      if (step._uid === uid) return { node: step, list: steps, index, parent };
      for (const key of ['then', 'else', 'body']) {
        if (Array.isArray(step[key])) {
          const found = findNode(uid, step[key], step);
          if (found) return found;
        }
      }
    }
    return null;
  }

  function opSpec(op) {
    return state.opMap[op] || { label: op, params: [], desc: '' };
  }

  function defaultStep(op) {
    const spec = opSpec(op);
    const step = { _uid: newUid(), id: '', op, title: spec.label, enabled: true, comment: '' };
    (spec.params || []).forEach((param) => {
      if (param.type === 'block') {
        step[param.key] = [];
      } else if (param.type === 'cond') {
        step[param.key] = { left: '', op: 'truthy', right: '' };
      } else if (param.default !== undefined) {
        step[param.key] = param.default;
      } else if (param.type === 'bool') {
        step[param.key] = false;
      } else if (param.type === 'int' || param.type === 'float') {
        step[param.key] = 0;
      } else {
        step[param.key] = '';
      }
    });
    return step;
  }

  function describeStep(step) {
    const spec = opSpec(step.op);
    const parts = [];
    (spec.params || []).forEach((param) => {
      if (param.type === 'block') return;
      const value = step[param.key];
      if (value === undefined || value === '' || value === null) return;
      if (param.type === 'cond') {
        const cond = value || {};
        parts.push(`${cond.left || '?'} ${cond.op || 'truthy'} ${cond.right ?? ''}`.trim());
        return;
      }
      if (param.type === 'bool' && value === param.default) return;
      parts.push(String(value));
    });
    return parts.join(' · ');
  }

  // ---------------------------------------------------------------- 树渲染
  function renderTree() {
    const root = $('stepTree');
    root.innerHTML = '';
    const steps = (state.flow && state.flow.steps) || [];
    if (!steps.length) {
      const hint = document.createElement('p');
      hint.className = 'hint';
      hint.textContent = '还没有步骤，先在上面选一个类型添加';
      root.appendChild(hint);
      return;
    }
    renderBlock(root, steps);
  }

  function renderBlock(container, steps) {
    steps.forEach((step) => {
      const row = document.createElement('div');
      row.className = 'step-row' + (step._uid === state.selectedUid ? ' selected' : '');
      row.dataset.uid = step._uid;
      if (step.enabled === false) row.style.opacity = '0.45';

      const idEl = document.createElement('span');
      idEl.className = 'step-id';
      idEl.textContent = step.id || '-';
      const labelEl = document.createElement('span');
      labelEl.className = 'step-label';
      labelEl.textContent = step.title || opSpec(step.op).label;
      const argsEl = document.createElement('span');
      argsEl.className = 'step-args';
      argsEl.textContent = describeStep(step);

      row.appendChild(idEl);
      row.appendChild(labelEl);
      row.appendChild(argsEl);

      if (step.op === 'if' || step.op === 'loop') {
        const addBtn = document.createElement('button');
        addBtn.className = 'step-add';
        addBtn.textContent = '+';
        addBtn.title = step.op === 'if' ? '往「满足时」里加子步骤' : '往循环体里加子步骤';
        addBtn.onclick = (event) => {
          event.stopPropagation();
          addChildStep(step, step.op === 'if' ? 'then' : 'body');
        };
        row.appendChild(addBtn);
      }

      row.onclick = () => selectStep(step._uid);
      container.appendChild(row);

      const blocks = [];
      if (step.op === 'if') {
        blocks.push(['then', '满足时']);
        blocks.push(['else', '否则']);
      } else if (step.op === 'loop') {
        blocks.push(['body', '循环体']);
      }
      blocks.forEach(([key, title]) => {
        const block = document.createElement('div');
        block.className = 'step-block';
        const titleEl = document.createElement('div');
        titleEl.className = 'step-block-title';
        titleEl.textContent = `${title} (${(step[key] || []).length})`;
        block.appendChild(titleEl);
        renderBlock(block, step[key] || []);
        container.appendChild(block);
      });
    });
  }

  function selectStep(uid) {
    state.selectedUid = uid;
    renderTree();
    renderForm();
  }

  // ---------------------------------------------------------------- 参数表单
  function ruleOptionsFor(op) {
    const kinds = (state.ruleKinds || {})[op] || null;
    return state.rules.filter((rule) => !kinds || kinds.includes(rule.kind));
  }

  function renderForm() {
    const host = $('stepForm');
    host.innerHTML = '';
    const found = state.selectedUid ? findNode(state.selectedUid) : null;
    if (!found) {
      $('editorTitle').textContent = '步骤参数';
      const hint = document.createElement('p');
      hint.className = 'hint';
      hint.textContent = '在左侧选择一个步骤';
      host.appendChild(hint);
      return;
    }
    const step = found.node;
    const spec = opSpec(step.op);
    $('editorTitle').textContent = `${step.id || '-'} · ${spec.label}`;

    host.appendChild(fieldText('标题', step.title, (value) => {
      step.title = value;
      renderTree();
    }, spec.desc));

    const enabledField = document.createElement('div');
    enabledField.className = 'field';
    const enabledLabel = document.createElement('label');
    const enabledBox = document.createElement('input');
    enabledBox.type = 'checkbox';
    enabledBox.checked = step.enabled !== false;
    enabledBox.onchange = () => {
      step.enabled = enabledBox.checked;
      renderTree();
    };
    enabledLabel.appendChild(enabledBox);
    enabledLabel.appendChild(document.createTextNode(' 启用这一步'));
    enabledField.appendChild(enabledLabel);
    host.appendChild(enabledField);

    (spec.params || []).forEach((param) => {
      if (param.type === 'block') {
        const blockField = document.createElement('div');
        blockField.className = 'field';
        const blockLabel = document.createElement('label');
        blockLabel.textContent = param.label || param.key;
        blockField.appendChild(blockLabel);
        const countLine = document.createElement('div');
        countLine.className = 'field-desc';
        countLine.textContent = `当前 ${(step[param.key] || []).length} 个子步骤（在左侧树里编辑）`;
        blockField.appendChild(countLine);
        host.appendChild(blockField);
        return;
      }
      host.appendChild(buildParamField(step, param));
    });
  }

  function fieldText(labelText, value, onChange, desc) {
    const field = document.createElement('div');
    field.className = 'field';
    const label = document.createElement('label');
    label.textContent = labelText;
    const input = document.createElement('input');
    input.type = 'text';
    input.value = value == null ? '' : String(value);
    input.onchange = () => onChange(input.value);
    field.appendChild(label);
    field.appendChild(input);
    if (desc) {
      const hint = document.createElement('div');
      hint.className = 'field-desc';
      hint.textContent = desc;
      field.appendChild(hint);
    }
    return field;
  }

  function buildParamField(step, param) {
    const field = document.createElement('div');
    field.className = 'field';
    const label = document.createElement('label');
    label.textContent = `${param.label || param.key}${param.required ? ' *' : ''}`;
    field.appendChild(label);

    const refresh = () => { renderTree(); };

    if (param.type === 'cond') {
      const row = document.createElement('div');
      row.className = 'cond-row';
      const cond = step[param.key] || { left: '', op: 'truthy', right: '' };
      const leftInput = document.createElement('input');
      leftInput.type = 'text';
      leftInput.value = cond.left == null ? '' : String(cond.left);
      leftInput.placeholder = 'var:次数 / 字面量';
      leftInput.onchange = () => { cond.left = leftInput.value; step[param.key] = cond; refresh(); };
      const opSelect = document.createElement('select');
      state.compareOps.forEach((op) => {
        const option = document.createElement('option');
        option.value = op;
        option.textContent = op;
        opSelect.appendChild(option);
      });
      opSelect.value = cond.op || 'truthy';
      opSelect.onchange = () => { cond.op = opSelect.value; step[param.key] = cond; refresh(); };
      const rightInput = document.createElement('input');
      rightInput.type = 'text';
      rightInput.value = cond.right == null ? '' : String(cond.right);
      rightInput.placeholder = '右值（可空）';
      rightInput.onchange = () => { cond.right = rightInput.value; step[param.key] = cond; refresh(); };
      row.appendChild(leftInput);
      row.appendChild(opSelect);
      row.appendChild(rightInput);
      field.appendChild(row);
      return field;
    }

    if (param.type === 'enum') {
      const select = document.createElement('select');
      (param.values || []).forEach((value) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
      select.value = step[param.key] != null ? String(step[param.key]) : (param.default || '');
      select.onchange = () => {
        step[param.key] = select.value;
        refresh();
      };
      field.appendChild(select);
      return field;
    }

    if (param.type === 'bool') {
      const box = document.createElement('input');
      box.type = 'checkbox';
      box.checked = step[param.key] === undefined ? Boolean(param.default) : Boolean(step[param.key]);
      box.onchange = () => {
        step[param.key] = box.checked;
        refresh();
      };
      field.appendChild(box);
      return field;
    }

    if (param.type === 'rule') {
      const list = document.createElement('input');
      list.type = 'text';
      list.setAttribute('list', `rule-list-${param.key}`);
      list.value = step[param.key] == null ? '' : String(step[param.key]);
      list.placeholder = '选择或手填规则名';
      list.onchange = () => {
        step[param.key] = list.value.trim();
        refresh();
      };
      const datalist = document.createElement('datalist');
      datalist.id = `rule-list-${param.key}`;
      ruleOptionsFor(step.op).forEach((rule) => {
        const option = document.createElement('option');
        option.value = rule.const;
        option.label = `${rule.kind} · ${rule.item}`;
        datalist.appendChild(option);
      });
      field.appendChild(list);
      field.appendChild(datalist);
      const count = ruleOptionsFor(step.op).length;
      if (!count) {
        const hint = document.createElement('div');
        hint.className = 'field-desc';
        hint.textContent = '当前任务还没有匹配的规则，先去标注页保存规则';
        field.appendChild(hint);
      }
      return field;
    }

    if (param.key === 'page' && state.pages.length) {
      const select = document.createElement('select');
      const empty = document.createElement('option');
      empty.value = '';
      empty.textContent = '（选择页面）';
      select.appendChild(empty);
      state.pages.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
      });
      select.value = step[param.key] || '';
      select.onchange = () => {
        step[param.key] = select.value;
        refresh();
      };
      field.appendChild(select);
      return field;
    }

    const input = document.createElement('input');
    input.type = param.type === 'int' || param.type === 'float' ? 'number' : 'text';
    if (input.type === 'number') {
      input.step = param.type === 'int' ? '1' : '0.1';
    }
    input.value = step[param.key] == null ? '' : String(step[param.key]);
    input.onchange = () => {
      if (input.type === 'number') {
        const parsed = Number(input.value);
        step[param.key] = Number.isFinite(parsed) ? parsed : (param.default || 0);
      } else {
        step[param.key] = input.value;
      }
      refresh();
    };
    field.appendChild(input);
    if (param.desc) {
      const hint = document.createElement('div');
      hint.className = 'field-desc';
      hint.textContent = param.desc;
      field.appendChild(hint);
    }
    return field;
  }

  // ---------------------------------------------------------------- 结构编辑
  function addStepAtEnd() {
    const op = $('addOpSelect').value;
    if (!op) return;
    const step = defaultStep(op);
    if (!state.flow) state.flow = { name: '', task: '', vars: {}, steps: [] };
    state.flow.steps.push(step);
    renumber(state.flow.steps);
    state.selectedUid = step._uid;
    renderTree();
    renderForm();
    markDirty();
  }

  function addChildStep(parentStep, key) {
    const op = $('addOpSelect').value || 'log';
    const step = defaultStep(op);
    if (!Array.isArray(parentStep[key])) parentStep[key] = [];
    parentStep[key].push(step);
    renumber(state.flow.steps);
    state.selectedUid = step._uid;
    renderTree();
    renderForm();
    markDirty();
  }

  function moveSelected(delta) {
    const found = state.selectedUid ? findNode(state.selectedUid) : null;
    if (!found) return;
    const target = found.index + delta;
    if (target < 0 || target >= found.list.length) return;
    const [node] = found.list.splice(found.index, 1);
    found.list.splice(target, 0, node);
    renumber(state.flow.steps);
    renderTree();
    renderForm();
    markDirty();
  }

  function duplicateSelected() {
    const found = state.selectedUid ? findNode(state.selectedUid) : null;
    if (!found) return;
    const clone = JSON.parse(JSON.stringify(serializeSteps([found.node])[0]));
    assignUids([clone]);
    found.list.splice(found.index + 1, 0, clone);
    renumber(state.flow.steps);
    state.selectedUid = clone._uid;
    renderTree();
    renderForm();
    markDirty();
  }

  function deleteSelected() {
    const found = state.selectedUid ? findNode(state.selectedUid) : null;
    if (!found) return;
    found.list.splice(found.index, 1);
    state.selectedUid = null;
    renumber(state.flow.steps);
    renderTree();
    renderForm();
    markDirty();
  }

  function markDirty() {
    setStatus('未保存');
  }

  // ---------------------------------------------------------------- 流程加载/保存
  async function loadFlows(selectName) {
    const data = await apiGet(`${FLOW_API}/list`);
    state.flows = data.flows || [];
    const select = $('flowSelect');
    select.innerHTML = '';
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = '（选择流程）';
    select.appendChild(empty);
    state.flows.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.name;
      option.textContent = item.error ? `${item.name} (损坏)` : `${item.name} (${item.steps} 步)`;
      select.appendChild(option);
    });
    const target = selectName || (state.flows[0] && state.flows[0].name);
    if (target) {
      select.value = target;
      await loadFlow(target);
    }
  }

  async function loadFlow(name) {
    const data = await apiGet(`${FLOW_API}/flow/${encodeURIComponent(name)}`);
    const flow = data.flow;
    assignUids(flow.steps || []);
    state.flow = flow;
    state.selectedUid = null;
    $('flowName').value = flow.name || name;
    $('varsInput').value = JSON.stringify(flow.vars || {}, null, 2);
    if (flow.task) {
      $('taskSelect').value = flow.task;
      await loadRules(flow.task);
    }
    renderTree();
    renderForm();
    setStatus(`已载入 ${name}`);
  }

  async function saveFlow() {
    const name = ($('flowName').value || '').trim();
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(name)) {
      setStatus('流程名只能包含字母数字-_', true);
      return;
    }
    const flow = serializeFlow();
    flow.name = name;
    flow.task = currentTask();
    try {
      const data = await apiPost(`${FLOW_API}/save`, { name, flow });
      state.flow = data.flow;
      assignUids(state.flow.steps || []);
      state.selectedUid = null;
      $('varsInput').value = JSON.stringify(state.flow.vars || {}, null, 2);
      renderTree();
      renderForm();
      await loadFlows(name);
      $('flowName').value = name;
      setStatus('已保存');
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  function newFlow() {
    const name = ($('flowName').value || '').trim() || `flow_${Date.now().toString().slice(-6)}`;
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(name)) {
      setStatus('流程名只能包含字母数字-_', true);
      return;
    }
    state.flow = { name, task: currentTask(), vars: {}, steps: [] };
    state.selectedUid = null;
    $('flowName').value = name;
    $('varsInput').value = '{}';
    renderTree();
    renderForm();
    setStatus('新流程，记得保存');
  }

  async function deleteFlow() {
    const name = ($('flowSelect').value || '').trim();
    if (!name) return;
    if (!window.confirm(`删除流程 ${name}？`)) return;
    try {
      await apiPost(`${FLOW_API}/delete`, { name });
      state.flow = null;
      await loadFlows();
      setStatus('已删除');
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  function currentTask() {
    return ($('taskSelect').value || (state.flow && state.flow.task) || '').trim();
  }

  async function loadRules(task) {
    try {
      const data = await apiGet(`${FLOW_API}/rules?task=${encodeURIComponent(task || '')}`);
      state.rules = data.rules || [];
    } catch (error) {
      state.rules = [];
      setStatus(`规则加载失败: ${error.message}`, true);
    }
    renderForm();
  }

  // ---------------------------------------------------------------- 模拟器连接
  function openWs() {
    closeWs();
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/tool/annotator/ws/${state.sessionId}`;
    const ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === 'error') setStatus(`采集错误: ${payload.message}`, true);
        } catch (error) { /* ignore */ }
        return;
      }
      drawFrame(event.data);
    };
    ws.onclose = () => {
      state.ws = null;
      $('frameHint').textContent = '已断开';
      $('frameHint').style.display = 'block';
    };
    state.ws = ws;
  }

  function closeWs() {
    if (state.ws) {
      try { state.ws.close(); } catch (error) { /* ignore */ }
      state.ws = null;
    }
  }

  async function drawFrame(buffer) {
    const blob = new Blob([buffer], { type: 'image/jpeg' });
    const bitmap = await createImageBitmap(blob);
    const canvas = $('frameCanvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    canvas.getContext('2d').drawImage(bitmap, 0, 0);
    $('frameHint').style.display = 'none';
  }

  async function connectEmulator() {
    const config = $('configSelect').value;
    if (!config) {
      setStatus('先选择配置', true);
      return;
    }
    try {
      if (!state.sessionId) {
        const data = await apiPost(`${ANNOTATOR_API}/session`);
        state.sessionId = data.session.session_id;
      }
      await apiPost(`${ANNOTATOR_API}/emulator/start`, {
        session_id: state.sessionId,
        config_name: config,
        frame_rate: 2,
      });
      $('frameHint').textContent = '连接中…';
      $('frameHint').style.display = 'block';
      openWs();
      setStatus('模拟器已连接');
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  async function disconnectEmulator() {
    closeWs();
    if (!state.sessionId) return;
    try {
      await apiPost(`${ANNOTATOR_API}/emulator/stop`, { session_id: state.sessionId });
    } catch (error) {
      setStatus(error.message, true);
    }
    $('frameHint').textContent = '已断开';
    $('frameHint').style.display = 'block';
  }

  // ---------------------------------------------------------------- 运行 / 生成
  function logLine(text, className = '') {
    const log = $('runLog');
    const line = document.createElement('div');
    if (className) line.className = className;
    line.textContent = text;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  function clearLog() {
    $('runLog').innerHTML = '';
  }

  async function runSelectedStep() {
    const found = state.selectedUid ? findNode(state.selectedUid) : null;
    if (!found) {
      setStatus('先选一个步骤', true);
      return;
    }
    if (!state.sessionId) {
      setStatus('先连接模拟器（或用标注页上传图片）', true);
      return;
    }
    clearLog();
    const flow = serializeFlow();
    const stepId = found.node.id;
    logLine(`执行 ${stepId} · ${opSpec(found.node.op).label}`, 'dim');
    try {
      const result = await apiPost(`${FLOW_API}/test`, {
        session_id: state.sessionId,
        flow,
        step_id: stepId,
        task: currentTask(),
        execute: $('executeChk').checked,
      });
      state.lastStepResult = result;
      (result.steps || []).forEach((step) => {
        const mark = step.ok ? 'OK' : 'FAIL';
        const prefix = step.depth ? '  '.repeat(step.depth) : '';
        logLine(`${prefix}[${mark}] ${step.stepId} ${step.op} · ${step.message || ''}`, step.ok ? 'ok' : 'fail');
      });
      if (result.error) logLine(`错误: ${result.error}`, 'fail');
      if ((result.actions || []).length) {
        logLine(`动作: ${result.actions.map((action) => action.type).join(', ')}`, 'dim');
      }
      if ((result.sent || []).length) {
        logLine(`已下发设备: ${result.sent.length} 个`, 'ok');
      }
      const vars = result.vars || {};
      const keys = Object.keys(vars);
      if (keys.length) logLine(`变量: ${keys.map((key) => `${key}=${vars[key]}`).join(' | ')}`, 'dim');
      setStatus(result.ok ? '本步通过' : '本步未通过', !result.ok);
    } catch (error) {
      logLine(error.message, 'fail');
      setStatus(error.message, true);
    }
  }

  async function generateTask() {
    const task = ($('genTask').value || '').trim();
    if (!task) {
      setStatus('先填目标任务名', true);
      return;
    }
    try {
      const flow = serializeFlow();
      // 注意：flow.task 是规则来源任务，生成目标单独用 task 传，避免把规则来源覆盖掉
      const result = await apiPost(`${FLOW_API}/generate`, { flow, task });
      $('genCode').textContent = result.code || '';
      const copied = result.copied || {};
      const copiedMsg = copied.items || copied.images
        ? `，复制规则 ${copied.items} 条 / 图片 ${copied.images} 张`
        : '';
      const assetsMsg = result.assets_status === 'failed' ? '（assets 生成失败）' : '';
      logLine(`已生成 ${result.path}（规则来自 ${result.source_task || flow.task}）${copiedMsg}${assetsMsg}`, 'ok');
      const reg = result.registration || {};
      if (reg.config === 'created' || reg.config_model === 'patched') {
        logLine('新任务已登记进配置（config.py + config_model.py），重启 OAS 后「自定义流程」菜单里可见', 'ok');
      }
      setStatus('已生成任务代码');
    } catch (error) {
      setStatus(error.message, true);
    }
  }

  // ---------------------------------------------------------------- 初始化
  async function loadOps() {
    const data = await apiGet(`${FLOW_API}/ops`);
    state.ops = data.ops || [];
    state.compareOps = data.compare_ops || [];
    state.varPrefix = data.var_prefix || 'var:';
    state.ruleKinds = {};
    state.ops.forEach((spec) => {
      state.opMap[spec.op] = spec;
      if (spec.rule_kinds) state.ruleKinds[spec.op] = spec.rule_kinds;
    });
    const select = $('addOpSelect');
    select.innerHTML = '';
    state.ops.forEach((spec) => {
      const option = document.createElement('option');
      option.value = spec.op;
      option.textContent = `${spec.label}（${spec.op}）`;
      select.appendChild(option);
    });
  }

  async function loadTasks() {
    const data = await apiGet(`${FLOW_API}/tasks`);
    state.tasks = data.tasks || [];
    const select = $('taskSelect');
    select.innerHTML = '';
    state.tasks.forEach((name) => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      select.appendChild(option);
    });
    if (state.tasks.includes('CustomFlow')) select.value = 'CustomFlow';
  }

  async function loadPages() {
    try {
      const data = await apiGet(`${FLOW_API}/pages`);
      state.pages = data.pages || [];
    } catch (error) {
      state.pages = [];
    }
  }

  async function loadConfigs() {
    try {
      const data = await apiGet(`${ANNOTATOR_API}/configs`);
      state.configs = data.configs || data || [];
      const select = $('configSelect');
      select.innerHTML = '';
      (state.configs || []).forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
      });
    } catch (error) {
      setStatus(`配置列表读取失败: ${error.message}`, true);
    }
  }

  function bindEvents() {
    $('addStepBtn').onclick = addStepAtEnd;
    $('moveUpBtn').onclick = () => moveSelected(-1);
    $('moveDownBtn').onclick = () => moveSelected(1);
    $('dupStepBtn').onclick = duplicateSelected;
    $('delStepBtn').onclick = deleteSelected;
    $('saveFlowBtn').onclick = saveFlow;
    $('newFlowBtn').onclick = newFlow;
    $('delFlowBtn').onclick = deleteFlow;
    $('flowSelect').onchange = () => {
      const name = $('flowSelect').value;
      if (name) loadFlow(name).catch((error) => setStatus(error.message, true));
    };
    $('taskSelect').onchange = async () => {
      if (state.flow) state.flow.task = currentTask();
      await loadRules(currentTask());
      markDirty();
    };
    $('varsInput').onchange = () => {
      try {
        const parsed = JSON.parse($('varsInput').value || '{}');
        state.flow.vars = parsed;
        setStatus('变量已更新');
      } catch (error) {
        setStatus(`变量不是合法 JSON: ${error.message}`, true);
      }
    };
    $('startBtn').onclick = connectEmulator;
    $('stopBtn').onclick = disconnectEmulator;
    $('runStepBtn').onclick = runSelectedStep;
    $('genBtn').onclick = generateTask;
  }

  async function init() {
    bindEvents();
    try {
      await Promise.all([loadOps(), loadTasks(), loadPages(), loadConfigs()]);
    } catch (error) {
      setStatus(`初始化失败: ${error.message}`, true);
      return;
    }
    await loadRules(currentTask());
    try {
      await loadFlows();
    } catch (error) {
      setStatus(`流程列表读取失败: ${error.message}`, true);
    }
  }

  window.addEventListener('DOMContentLoaded', init);
})();
