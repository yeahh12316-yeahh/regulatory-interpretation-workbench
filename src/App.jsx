import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Building2,
  Bell,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  Download,
  ExternalLink,
  FileUp,
  FileText,
  Filter,
  FolderOpen,
  Home,
  KeyRound,
  LogOut,
  Lock,
  MoreVertical,
  Network,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  RefreshCw,
  Save,
  SlidersHorizontal,
  Sparkles,
  UserRound,
  Users,
  X,
} from 'lucide-react'
import { apiClient } from './lib/api-client'
import { runtimeConfig } from './lib/runtime-config'
import { chooseCurrentTask, mapApiTaskToWorkbenchTask } from './lib/task-persistence'

const tasks = [
  {
    id: 'case-001',
    title: '金融企业呆账核销管理办法（2017年版）解读',
    institution: '商业银行',
    status: '处理中',
    updated: '2026-08-21',
    state: 'active',
  },
  {
    id: 'case-002',
    title: '待创建外规解读任务',
    institution: '未选择机构类型',
    status: '未开始',
    updated: '—',
    state: 'idle',
  },
]

const initialEvidence = [
  {
    id: 'E-01',
    title: '用户提供 PDF：2017 年版正文',
    type: '用户上传文件',
    location: '财政部关于印发…通知.pdf · 第1—4页',
    note: '正文覆盖第一条至第二十五条；当前任务不启用 S5。',
    tone: 'green',
  },
  {
    id: 'E-02',
    title: '2017 年版来源页：财政部转载',
    type: '官方协会转载页',
    location: '中国财务公司协会 · 2017-08-31',
    note: '用于交叉核验发布机关、文号、正文和施行日期。',
    tone: 'green',
  },
]

const toc = [
  { label: '第一章　总则', open: false },
  { label: '第二章　呆账认定', open: true, children: ['认定原则', '认定条件', '核销材料'] },
  { label: '第三章　呆账核销', open: true, children: ['核销权限', '核销程序', '核销后的管理'] },
  { label: '第四章　监督与责任', open: false },
  { label: '第五章　附则', open: false },
]

const SESSION_STORAGE_KEY = 'regulatory-workbench-session'
const CURRENT_TASK_STORAGE_KEY = 'regulatory-workbench-current-task'

function readSession() {
  try {
    return JSON.parse(window.localStorage.getItem(SESSION_STORAGE_KEY) || 'null')
  } catch {
    return null
  }
}

function demoSession() {
  return {
    mode: 'preview',
    accessToken: '',
    user: { user_id: 'preview-user', email: 'preview@example.com', display_name: '前端预览用户', is_active: true },
    organization: { organization_id: 'preview-org', name: '示例机构空间', slug: 'preview-org', is_active: true },
  }
}

function persistSession(session) {
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
}

function readCurrentTaskId() {
  try {
    return window.localStorage.getItem(CURRENT_TASK_STORAGE_KEY) || null
  } catch {
    return null
  }
}

function persistCurrentTaskId(taskId) {
  if (!taskId) return
  try {
    window.localStorage.setItem(CURRENT_TASK_STORAGE_KEY, taskId)
  } catch {
    // A private browsing context may reject local persistence; the API remains authoritative.
  }
}

function AuthScreen({ onAuthenticated, onPreview }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ email: '', password: '', display_name: '', organization_name: '', organization_slug: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      const payload = mode === 'login'
        ? { email: form.email, password: form.password }
        : form
      const auth = mode === 'login' ? await apiClient.login(payload) : await apiClient.register(payload)
      const organization = await apiClient.currentOrganization(auth.access_token)
      const session = { mode: 'api', accessToken: auth.access_token, user: auth.user, organization }
      persistSession(session)
      onAuthenticated(session)
    } catch (requestError) {
      setError(requestError.message || '无法连接认证服务，请检查后端地址。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <img className="deloitte-logo" src={`${import.meta.env.BASE_URL}assets/deloitte-logo-white.png`} alt="Deloitte" />
          <span>外规解读智能体工作台</span>
        </div>
        <div className="auth-kicker">SECURE WORKSPACE ACCESS</div>
        <h1>{mode === 'login' ? '登录工作台' : '创建机构空间'}</h1>
        <p className="auth-description">登录后，任务、法规证据和解读交付物将按机构空间进行隔离。</p>
        <div className="auth-tabs">
          <button className={mode === 'login' ? 'is-active' : ''} onClick={() => { setMode('login'); setError('') }}>登录</button>
          <button className={mode === 'register' ? 'is-active' : ''} onClick={() => { setMode('register'); setError('') }}>注册机构空间</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === 'register' && <>
            <label>姓名<input value={form.display_name} onChange={(event) => update('display_name', event.target.value)} placeholder="例如：张三" required /></label>
            <label>机构空间名称<input value={form.organization_name} onChange={(event) => update('organization_name', event.target.value)} placeholder="例如：某某金融机构" required /></label>
            <label>机构空间标识<input value={form.organization_slug} onChange={(event) => update('organization_slug', event.target.value)} placeholder="例如：my-finance-org" pattern="[a-z0-9-]+" required /></label>
          </>}
          <label>邮箱<input type="email" value={form.email} onChange={(event) => update('email', event.target.value)} placeholder="name@company.com" required /></label>
          <label>密码<input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} placeholder="至少 10 位" minLength={mode === 'login' ? 1 : 10} required /></label>
          {error && <div className="auth-error"><AlertCircle size={15} />{error}</div>}
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? '正在连接…' : mode === 'login' ? '登录工作台' : '创建并进入工作台'} <ArrowRight size={16} /></button>
        </form>
        {!runtimeConfig.apiConfigured && <div className="preview-callout">
          <div><strong>当前未配置后端地址</strong><span>可先进入前端预览，体验工作台的机构与权限入口。</span></div>
          <button onClick={onPreview}>进入前端预览</button>
        </div>}
        <div className="auth-footer"><KeyRound size={14} /> 认证、机构和角色权限由后端 API 控制</div>
      </div>
    </div>
  )
}

function AccessPanel({ session, onClose, onSessionChange, onLogout, notify }) {
  const [organizations, setOrganizations] = useState([session.organization])
  const [members, setMembers] = useState([])
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState('viewer')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (session.mode !== 'api') {
      setMembers([
        { member_id: 'preview-member', user_id: 'preview-user', email: session.user.email, display_name: session.user.display_name, role: 'owner' },
        { member_id: 'preview-reviewer', user_id: 'preview-reviewer', email: 'reviewer@example.com', display_name: '预览复核成员', role: 'reviewer' },
      ])
      return
    }
    let cancelled = false
    Promise.all([apiClient.organizations(session.accessToken), apiClient.members(session.accessToken)])
      .then(([nextOrganizations, nextMembers]) => {
        if (!cancelled) { setOrganizations(nextOrganizations); setMembers(nextMembers) }
      })
      .catch((requestError) => { if (!cancelled) setError(requestError.message) })
    return () => { cancelled = true }
  }, [session])

  async function switchOrganization(organization) {
    if (organization.organization_id === session.organization.organization_id) return
    if (session.mode !== 'api') {
      const nextSession = { ...session, organization }
      persistSession(nextSession)
      onSessionChange(nextSession)
      notify(`已切换机构空间：${organization.name}`)
      return
    }
    setBusy(true)
    try {
      const auth = await apiClient.switchOrganization(session.accessToken, organization.organization_id)
      const nextSession = { ...session, accessToken: auth.access_token, user: auth.user, organization }
      persistSession(nextSession)
      onSessionChange(nextSession)
      notify(`已切换机构空间：${organization.name}`)
    } catch (requestError) { setError(requestError.message) } finally { setBusy(false) }
  }

  async function addMember(event) {
    event.preventDefault()
    if (session.mode !== 'api') { notify('预览模式仅展示成员和角色界面'); return }
    setBusy(true)
    try {
      const member = await apiClient.addMember(session.accessToken, { email: memberEmail, role: memberRole })
      setMembers((current) => [...current, member])
      setMemberEmail('')
      notify('成员已加入当前机构空间')
    } catch (requestError) { setError(requestError.message) } finally { setBusy(false) }
  }

  async function updateRole(member, role) {
    if (session.mode !== 'api') { setMembers((current) => current.map((item) => item.member_id === member.member_id ? { ...item, role } : item)); return }
    try {
      const updated = await apiClient.updateMemberRole(session.accessToken, member.member_id, { role })
      setMembers((current) => current.map((item) => item.member_id === member.member_id ? updated : item))
      notify('角色已更新')
    } catch (requestError) { setError(requestError.message) }
  }

  return <div className="access-overlay" onClick={onClose}>
    <section className="access-panel" onClick={(event) => event.stopPropagation()}>
      <div className="access-panel-header"><div><span className="auth-kicker">WORKSPACE CONTROL</span><h2>机构空间与权限</h2></div><IconButton label="关闭机构权限面板" onClick={onClose}><X size={18} /></IconButton></div>
      {error && <div className="panel-error"><AlertCircle size={15} />{error}</div>}
      <div className="access-section"><div className="access-section-title"><Building2 size={16} /> 我的机构空间</div>
        <div className="organization-list">{organizations.map((organization) => <button key={organization.organization_id} className={`organization-item ${organization.organization_id === session.organization.organization_id ? 'is-current' : ''}`} onClick={() => switchOrganization(organization)} disabled={busy}><span>{organization.name}</span><small>{organization.organization_id === session.organization.organization_id ? '当前空间' : '切换'}</small></button>)}</div>
      </div>
      <div className="access-section"><div className="access-section-title"><Users size={16} /> 成员与角色 <span>{members.length} 人</span></div>
        <div className="member-list">{members.map((member) => <div className="member-row" key={member.member_id}><div className="member-avatar"><UserRound size={14} /></div><div className="member-main"><strong>{member.display_name || member.email || member.user_id}</strong><small>{member.email || member.user_id}</small></div><select value={member.role} onChange={(event) => updateRole(member, event.target.value)} disabled={member.role === 'owner'}><option value="owner">所有者</option><option value="admin">管理员</option><option value="editor">编辑者</option><option value="reviewer">复核者</option><option value="viewer">查看者</option></select></div>)}</div>
        <form className="add-member-form" onSubmit={addMember}><input type="email" value={memberEmail} onChange={(event) => setMemberEmail(event.target.value)} placeholder="输入已注册成员邮箱" required /><select value={memberRole} onChange={(event) => setMemberRole(event.target.value)}><option value="viewer">查看者</option><option value="reviewer">复核者</option><option value="editor">编辑者</option><option value="admin">管理员</option></select><button type="submit" disabled={busy}><Plus size={15} /> 添加</button></form>
      </div>
      <div className="access-note"><ShieldCheck size={15} /> 任务、法规和证据访问均由当前机构空间及成员角色控制。</div>
      <button className="logout-button" onClick={onLogout}><LogOut size={15} /> 退出登录</button>
    </section>
  </div>
}

function IconButton({ label, children, onClick, active = false }) {
  return (
    <button className={`icon-button ${active ? 'is-active' : ''}`} aria-label={label} title={label} onClick={onClick}>
      {children}
    </button>
  )
}

function StatusTag({ children, tone = 'neutral' }) {
  return <span className={`status-tag status-${tone}`}>{children}</span>
}

function RegulationImportModal({ session, onClose, onImported, taskId = null, regulationId = null, versionRole = 'current' }) {
  const [file, setFile] = useState(null)
  const [versionLabel, setVersionLabel] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [failedUpload, setFailedUpload] = useState(null)
  const [uploadId] = useState(() => window.crypto?.randomUUID?.() || `upload-${Date.now()}-${Math.random().toString(16).slice(2)}`)

  async function submit(event) {
    event.preventDefault()
    setError('')
    setFailedUpload(null)
    if (!file) {
      setError('请先选择法规 PDF')
      return
    }
    if (!runtimeConfig.apiConfigured) {
      setError('当前前端未配置私有 API 地址；请在私有部署构建时设置 VITE_API_BASE_URL。')
      return
    }
    setBusy(true)
    try {
      const nextResult = await apiClient.importRegulation(file, { taskId, regulationId, versionLabel, versionRole, sourceUrl, uploadId }, session.accessToken)
      setResult(nextResult)
      onImported(nextResult)
    } catch (requestError) {
      setError(requestError.message || '法规上传或解析失败')
      if (requestError.retryable && requestError.documentId) {
        setFailedUpload({ documentId: requestError.documentId })
      }
    } finally {
      setBusy(false)
    }
  }

  async function retryParse() {
    if (!failedUpload) return
    setBusy(true)
    setError('')
    try {
      const nextResult = await apiClient.retryRegulationParse(failedUpload.documentId, session.accessToken)
      setFailedUpload(null)
      setResult(nextResult)
      onImported(nextResult)
    } catch (requestError) {
      setError(requestError.message || '重新解析失败')
      if (requestError.retryable && requestError.documentId) setFailedUpload({ documentId: requestError.documentId })
    } finally {
      setBusy(false)
    }
  }

  return <div className="modal-overlay" onClick={onClose}>
    <section className="regulation-import-modal" onClick={(event) => event.stopPropagation()}>
      <div className="modal-header">
        <div><span className="modal-kicker">STEP 9 · INPUT</span><h2>{versionRole === 'previous' ? '补充旧规原文' : '上传法规原文'}</h2></div>
        <IconButton label="关闭法规上传" onClick={onClose}><X size={18} /></IconButton>
      </div>
      {!result ? <form className="import-form" onSubmit={submit}>
        <p className="modal-description">上传 PDF 后，系统会先唤醒并检查公开服务，再保存原文件、计算哈希和提取页面文本；扫描页会尝试 OCR 兜底，并把“第×条”原文保存为带页码/行号的可定位条款。</p>
        <label className="file-dropzone">
          <FileUp size={24} />
          <strong>{file ? file.name : '选择法规 PDF'}</strong>
          <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · 等待上传` : '仅支持 PDF，单文件不超过 25 MB'}</span>
          <input type="file" accept="application/pdf,.pdf" onChange={(event) => { setFile(event.target.files?.[0] || null); setError('') }} />
        </label>
        <label>版本标签（可选）<input value={versionLabel} onChange={(event) => setVersionLabel(event.target.value)} placeholder="例如：2017年版" /></label>
        <label>官方来源地址（可选）<input type="url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://..." /></label>
        <div className="import-boundary"><strong>本步处理范围</strong><span>{versionRole === 'previous' ? '该文件将登记为当前法规的前一版本，不会覆盖当前版本；完成上传后系统会重新运行 S1—S4，并在版本关系确认后运行 S5。' : '原文件不会因解析失败被删除；失败后可直接重新解析。OCR 提取的页面会标记为“需人工核验”，不会把 OCR 文字当作未经复核的正式结论。'}</span></div>
        {!runtimeConfig.apiConfigured && <div className="import-warning">当前公开预览没有连接后端，不会假装上传成功。私有部署配置 API 后，此按钮才会执行真实登记。</div>}
        {error && <div className="auth-error"><AlertCircle size={15} />{error}</div>}
        {failedUpload && <div className="import-retry"><strong>文件已安全保存，可继续重试</strong><span>来源文件编号：{failedUpload.documentId}</span><button type="button" className="modal-secondary" onClick={retryParse} disabled={busy}>{busy ? '重新解析中…' : '重新解析已保存文件'}</button></div>}
        <div className="modal-actions"><button type="button" className="modal-secondary" onClick={onClose}>取消</button><button type="submit" className="auth-submit" disabled={busy || !file || !runtimeConfig.apiConfigured}>{busy ? '正在上传并解析…' : '上传并登记'}</button></div>
      </form> : <div className="import-success">
        <div className="success-mark"><Check size={21} /></div>
        <h3>法规已登记，条款已生成</h3>
        <p>{result.regulation.title} · {result.version.version_label}</p>
        <div className="import-result-grid"><span>原文件</span><strong>{result.source_document.file_name}</strong><span>页数</span><strong>{result.page_count} 页</strong><span>条款</span><strong>{result.article_count} 条</strong><span>哈希</span><strong>{result.source_document.sha256.slice(0, 16)}…</strong></div>
        {result.warnings?.length > 0 && <div className="import-warning">{result.warnings.join('；')}</div>}
        <div className="sample-articles"><strong>已生成原文定位</strong>{result.sample_articles.map((article) => <div key={article.article_id}><span>{article.article_no}</span><small>第 {article.source_page} 页 · 行 {article.source_offset.line_start}—{article.source_offset.line_end}</small></div>)}</div>
        <div className="modal-actions"><button type="button" className="auth-submit" onClick={onClose}>返回工作台</button></div>
      </div>}
    </section>
  </div>
}

function ReviewPanel({ session, taskId, onClose, onReviewChanged, notify }) {
  const [review, setReview] = useState(null)
  const [contentPackage, setContentPackage] = useState(null)
  const [metadata, setMetadata] = useState({ document_no: '', issuer: '', publish_date: '', effective_date: '', attachment_resolution: '' })
  const [llmReview, setLlmReview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function loadReview() {
    if (!taskId || !runtimeConfig.apiConfigured) return
    setBusy(true)
    try {
      const nextReview = await apiClient.review(taskId, session?.accessToken)
      setReview(nextReview)
      const s1 = nextReview.stages?.S1?.output || {}
      setMetadata({
        document_no: s1.document_no || '',
        issuer: (s1.issuer || []).join('、'),
        publish_date: s1.publish_date || '',
        effective_date: s1.effective_date || '',
        attachment_resolution: nextReview.task?.processing_config?.review_overrides?.attachment_resolution || '',
      })
      onReviewChanged(nextReview)
    } catch (requestError) {
      setError(requestError.message || '无法读取人工复核数据')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { loadReview() }, [taskId])

  async function saveMetadata(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const nextReview = await apiClient.updateReviewMetadata(taskId, {
        document_no: metadata.document_no || null,
        issuer: metadata.issuer.split(/[、,，]/).map((item) => item.trim()).filter(Boolean),
        publish_date: metadata.publish_date || null,
        effective_date: metadata.effective_date || null,
        attachment_resolution: metadata.attachment_resolution || null,
      }, session?.accessToken)
      setReview(nextReview)
      onReviewChanged(nextReview)
      notify('法规元数据已保存并写入审计记录')
    } catch (requestError) { setError(requestError.message || '元数据保存失败') } finally { setBusy(false) }
  }

  async function saveRequirement(item) {
    setBusy(true)
    setError('')
    try {
      const updated = await apiClient.updateReviewRequirement(taskId, item.requirement_id, {
        subject: item.subject,
        action: item.action,
        object: item.object,
        condition: item.condition,
        deadline: item.deadline,
        frequency: item.frequency,
        threshold: item.threshold,
        exception: item.exception,
        evidence_required: item.evidence_required,
        review_status: item.review_status === 'reviewed' ? 'reviewed' : 'reviewing',
      }, session?.accessToken)
      setReview((current) => {
        const next = { ...current, requirements: current.requirements.map((requirement) => requirement.requirement_id === updated.requirement_id ? updated : requirement) }
        onReviewChanged(next)
        return next
      })
      notify(`已保存 ${item.article_id} 监管要求复核`)
    } catch (requestError) { setError(requestError.message || '监管要求保存失败') } finally { setBusy(false) }
  }

  async function saveInterpretation(item) {
    setBusy(true)
    setError('')
    try {
      const updated = await apiClient.updateReviewInterpretation(taskId, item.interpretation_id, {
        summary: item.summary,
        interpretation: item.interpretation,
        regulatory_meaning: item.regulatory_meaning,
        content_blocks: item.content_blocks,
        review_status: item.review_status === 'reviewed' ? 'reviewed' : 'reviewing',
        human_lock: item.human_lock,
      }, session?.accessToken)
      setReview((current) => {
        const replace = (candidate) => candidate.interpretation_id === updated.interpretation_id ? updated : candidate
        const next = { ...current, overall: replace(current.overall), article_interpretations: current.article_interpretations.map(replace) }
        onReviewChanged(next)
        return next
      })
      notify(`已保存 ${item.article_id || '整体'} 解读复核`)
    } catch (requestError) { setError(requestError.message || '解读保存失败') } finally { setBusy(false) }
  }

  async function verifyEvidence(evidence) {
    setBusy(true)
    setError('')
    try {
      const updated = await apiClient.updateReviewEvidence(taskId, evidence.evidence_id, { verification_status: 'verified' }, session?.accessToken)
      setReview((current) => {
        const next = { ...current, evidence: current.evidence.map(item => item.evidence_id === updated.evidence_id ? updated : item) }
        onReviewChanged(next)
        return next
      })
      notify(`已核验证据：${evidence.evidence_id}`)
    } catch (requestError) { setError(requestError.message || '证据核验失败') } finally { setBusy(false) }
  }

  async function runQc() {
    setBusy(true)
    setError('')
    try {
      await apiClient.runReviewQc(taskId, session?.accessToken)
      await loadReview()
      notify('QC 已完成，请查看阻断项和警示项')
    } catch (requestError) { setError(requestError.message || 'QC 执行失败') } finally { setBusy(false) }
  }

  async function runLlmReview() {
    setBusy(true)
    setError('')
    try {
      const result = await apiClient.runLlmReview(taskId, session?.accessToken)
      setLlmReview(result)
      await loadReview()
      notify(result.status === 'not_configured' ? 'LLM Reviewer 尚未配置，系统没有伪造模型通过' : `LLM Reviewer 返回：${result.status}`)
    } catch (requestError) { setError(requestError.message || 'LLM Reviewer 执行失败') } finally { setBusy(false) }
  }

  async function returnReview() {
    setBusy(true)
    setError('')
    try {
      await apiClient.reviewDecision(taskId, { decision: 'return', reason: '人工复核退回，需修改后重新审核' }, session?.accessToken)
      await loadReview()
      setContentPackage(null)
      notify('已退回修改；修改后请重新运行 QC')
    } catch (requestError) { setError(requestError.message || '退回失败') } finally { setBusy(false) }
  }

  async function publishReview() {
    setBusy(true)
    setError('')
    try {
      await apiClient.reviewDecision(taskId, { decision: 'publish', reason: '人工确认发布' }, session?.accessToken)
      await loadReview()
      notify('已通过发布闸门，任务状态为 published')
    } catch (requestError) { setError(requestError.message || '发布失败：请先通过 QC 并锁定 Content Package') } finally { setBusy(false) }
  }

  async function createContentPackage() {
    setBusy(true)
    setError('')
    try {
      const nextPackage = await apiClient.createContentPackage(taskId, session?.accessToken)
      setContentPackage(nextPackage)
      notify(`Content Package v${nextPackage.package_version} 已锁定`)
    } catch (requestError) {
      setError(requestError.detail?.missing ? `${requestError.message}：请先完成人工锁定、要求复核和证据核验` : (requestError.message || 'Content Package 生成失败'))
    } finally { setBusy(false) }
  }

  async function exportDocx() {
    setBusy(true)
    setError('')
    try {
      const report = await apiClient.exportDocx(taskId, session?.accessToken)
      setLastReport(report)
      window.open(`${runtimeConfig.apiBaseUrl}${report.download_url}`, '_blank', 'noopener,noreferrer')
      if (report.html_download_url) window.open(`${runtimeConfig.apiBaseUrl}${report.html_download_url}`, '_blank', 'noopener,noreferrer')
      await loadReview()
      notify('HTML 与 Word 交付物已生成，并通过一致性检查')
    } catch (requestError) { setError(requestError.message || '导出失败：请先通过 QC') } finally { setBusy(false) }
  }

  function changeRequirement(requirementId, field, value) {
    setReview((current) => ({ ...current, requirements: current.requirements.map(item => item.requirement_id === requirementId ? { ...item, [field]: value } : item) }))
  }

  function changeInterpretation(interpretationId, field, value) {
    setReview((current) => {
      const replace = (item) => item.interpretation_id === interpretationId ? { ...item, [field]: value } : item
      return { ...current, overall: replace(current.overall), article_interpretations: current.article_interpretations.map(replace) }
    })
  }

  if (!runtimeConfig.apiConfigured || !taskId) {
    return <div className="modal-overlay" onClick={onClose}><section className="review-panel" onClick={(event) => event.stopPropagation()}><div className="modal-header"><div><span className="modal-kicker">STEP 10 · REVIEW</span><h2>人工复核</h2></div><IconButton label="关闭人工复核" onClick={onClose}><X size={18} /></IconButton></div><div className="review-empty"><ShieldCheck size={28} /><strong>需要连接私有后端并先运行 S1—S4</strong><span>公开 Pages 不会伪造复核、QC 或导出结果。</span></div></section></div>
  }

  if (!review) {
    return <div className="modal-overlay" onClick={onClose}><section className="review-panel" onClick={(event) => event.stopPropagation()}><div className="modal-header"><div><span className="modal-kicker">STEP 10 · REVIEW</span><h2>人工复核</h2></div><IconButton label="关闭人工复核" onClick={onClose}><X size={18} /></IconButton></div><div className="review-empty"><RefreshCw className="spin" size={25} /><span>{error || '正在读取复核数据…'}</span></div></section></div>
  }

  const qc = review.qc_results?.find(item => item.check_type === 'REVIEW_GATE')
  const blockers = (review.qc_results || []).filter(item => item.status === 'blocker')
  const allInterpretations = [review.overall, ...review.article_interpretations]
  return <div className="modal-overlay" onClick={onClose}>
    <section className="review-panel" onClick={(event) => event.stopPropagation()}>
      <div className="modal-header"><div><span className="modal-kicker">STEP 10 · HUMAN REVIEW</span><h2>人工复核与交付闸门</h2></div><IconButton label="关闭人工复核" onClick={onClose}><X size={18} /></IconButton></div>
      <div className="review-toolbar"><div><strong>{review.task.task_name}</strong><span>所有修改保留原文、证据定位和审计记录{contentPackage ? ` · Content Package v${contentPackage.package_version} 已锁定` : ''}</span></div><div className="review-toolbar-actions"><StatusTag tone={review.task.task_status === 'ready_for_export' || review.task.task_status === 'published' ? 'green' : 'review'}>{review.task.task_status}</StatusTag><button className="review-small-button" onClick={returnReview} disabled={busy || review.task.task_status === 'published'}>退回修改</button><button className="review-small-button" onClick={runLlmReview} disabled={busy}><ShieldCheck size={14} /> {busy ? '处理中…' : '运行 LLM Reviewer'}</button><button className="review-small-button" onClick={createContentPackage} disabled={busy}><Lock size={14} /> {busy ? '处理中…' : '生成锁定内容包'}</button><button className="run-pipeline-button" onClick={runQc} disabled={busy}><ClipboardCheck size={15} /> {busy ? '处理中…' : '运行 QC'}</button><button className="outline-action review-export" onClick={exportDocx} disabled={busy || review.task.task_status !== 'ready_for_export'}><Download size={15} /> 导出 Word</button><button className="review-save" onClick={publishReview} disabled={busy || review.task.task_status !== 'ready_for_export'}>发布</button></div></div>
      {error && <div className="panel-error review-error"><AlertCircle size={15} />{error}</div>}
      {qc && <div className={`review-qc ${qc.status === 'blocker' ? 'is-blocked' : 'is-passed'}`}><div><strong>最近一次 QC：{qc.status}</strong><span>点击“运行 QC”会重新检查人工复核、证据、元数据和 S5 边界。</span></div><span>{blockers.length} 个阻断结果</span></div>}
      {llmReview && <div className={`review-qc ${llmReview.status === 'passed' ? 'is-passed' : 'is-blocked'}`}><div><strong>LLM Reviewer：{llmReview.status}</strong><span>{llmReview.status === 'not_configured' ? '未配置模型，不能声称完成模型复核。' : '模型结果仅作为复核意见，不能替代人工审核。'}</span></div><span>{llmReview.findings?.length || 0} 个发现</span></div>}
      <div className="review-body">
        <section className="review-section"><div className="review-section-title"><span>01</span><div><strong>元数据与边界</strong><small>机器识别结果保留来源和状态；待复核字段必须由人工确认，不从模型常识补齐。</small></div></div><div className="metadata-status-list">{Object.entries(review.stages?.S1?.output?.metadata_fields || {}).map(([field, item]) => <span key={field}><strong>{{ title: '标题', document_no: '文号', issuer: '发布机关', publish_date: '发布日期', effective_date: '生效日期' }[field] || field}</strong><StatusTag tone={item.status === 'manual_verified' ? 'green' : item.status === 'missing' || item.status === 'needs_review' ? 'review' : 'neutral'}>{item.status}</StatusTag><small>{item.extraction_method}{item.source_locator?.page ? ` · 第${item.source_locator.page}页` : ''}</small></span>)}</div><form className="review-form" onSubmit={saveMetadata}><label>文号<input value={metadata.document_no} onChange={(event) => setMetadata(current => ({ ...current, document_no: event.target.value }))} placeholder="待确认" /></label><label>发布机关<input value={metadata.issuer} onChange={(event) => setMetadata(current => ({ ...current, issuer: event.target.value }))} placeholder="例如：财政部" /></label><label>发布日期<input type="date" value={metadata.publish_date} onChange={(event) => setMetadata(current => ({ ...current, publish_date: event.target.value }))} /></label><label>生效日期<input type="date" value={metadata.effective_date} onChange={(event) => setMetadata(current => ({ ...current, effective_date: event.target.value }))} /></label><label>附件处理<select value={metadata.attachment_resolution} onChange={(event) => setMetadata(current => ({ ...current, attachment_resolution: event.target.value }))}><option value="">待补充官方附件</option><option value="confirmed_not_required">已确认本任务不涉及附件</option><option value="supplemented">已补充并核验附件</option><option value="needs_source">仍需补充来源</option></select></label><button className="review-save" type="submit" disabled={busy}><Save size={14} />保存元数据</button></form></section>
        <section className="review-section"><div className="review-section-title"><span>02</span><div><strong>整体解读</strong><small>必须保留 FACT / OFFICIAL / INTERPRETATION 内容块及其证据。</small></div></div><ReviewInterpretationCard item={review.overall} onChange={changeInterpretation} onSave={saveInterpretation} busy={busy} /></section>
        <section className="review-section"><div className="review-section-title"><span>03</span><div><strong>监管要求逐项复核</strong><small>原文片段不可编辑；主体、行为、条件、期限和例外可修订。</small></div></div><div className="review-items">{review.requirements.map((item) => <ReviewRequirementCard key={item.requirement_id} item={item} onChange={changeRequirement} onSave={saveRequirement} busy={busy} />)}</div></section>
        <section className="review-section"><div className="review-section-title"><span>04</span><div><strong>逐条解读与锁定</strong><small>每条解读必须人工复核并显式锁定，才能进入交付闸门。</small></div></div><div className="review-items">{allInterpretations.slice(1).map((item) => <ReviewInterpretationCard key={item.interpretation_id} item={item} onChange={changeInterpretation} onSave={saveInterpretation} busy={busy} />)}</div></section>
        <section className="review-section"><div className="review-section-title"><span>05</span><div><strong>证据核验</strong><small>点击“标记已核验”后，QC 才会允许进入可导出状态。</small></div></div><div className="review-evidence-list">{review.evidence.map((item) => <div className="review-evidence-row" key={item.evidence_id}><div><strong>{item.evidence_id}</strong><span>{item.locator?.article_no || '法规原文'} · 第{item.locator?.page || '待确认'}页</span></div><StatusTag tone={item.verification_status === 'verified' ? 'green' : 'review'}>{item.verification_status}</StatusTag><button className="review-small-button" onClick={() => verifyEvidence(item)} disabled={busy || item.verification_status === 'verified'}><ShieldCheck size={13} />{item.verification_status === 'verified' ? '已核验' : '标记已核验'}</button></div>)}</div></section>
      </div>
    </section>
  </div>
}

function ReviewRequirementCard({ item, onChange, onSave, busy }) {
  return <div className="review-item-card"><div className="review-item-head"><strong>{item.article_id}</strong><StatusTag tone={item.review_status === 'reviewed' ? 'green' : 'review'}>{item.review_status}</StatusTag></div><div className="review-original"><span>不可编辑的原文片段</span><p>{item.source_text}</p></div><div className="review-fields"><label>主体<input value={item.subject || ''} onChange={(event) => onChange(item.requirement_id, 'subject', event.target.value)} /></label><label>行为<input value={item.action || ''} onChange={(event) => onChange(item.requirement_id, 'action', event.target.value)} /></label><label>条件/例外<input value={[item.condition, item.exception].filter(Boolean).join('；')} onChange={(event) => onChange(item.requirement_id, 'condition', event.target.value)} /></label><label>时限/频率<input value={[item.deadline, item.frequency, item.threshold].filter(Boolean).join('；')} onChange={(event) => onChange(item.requirement_id, 'deadline', event.target.value)} /></label></div><div className="review-item-actions"><span>证据：{item.evidence_ids?.length || 1} 条 · 原文保持不变</span><button className="review-small-button" onClick={() => onChange(item.requirement_id, 'review_status', item.review_status === 'reviewed' ? 'reviewing' : 'reviewed')}><Check size={13} />{item.review_status === 'reviewed' ? '取消复核' : '标记已复核'}</button><button className="review-save" onClick={() => onSave(item)} disabled={busy}><Save size={13} />保存</button></div></div>
}

function ReviewInterpretationCard({ item, onChange, onSave, busy }) {
  return <div className="review-item-card"><div className="review-item-head"><strong>{item.article_id || '整体解读'}</strong><StatusTag tone={item.review_status === 'reviewed' && item.human_lock ? 'green' : 'review'}>{item.review_status === 'reviewed' && item.human_lock ? '已复核并锁定' : '待复核'}</StatusTag></div><label className="review-wide-label">摘要<input value={item.summary || ''} onChange={(event) => onChange(item.interpretation_id, 'summary', event.target.value)} /></label><label className="review-wide-label">解读<textarea rows="3" value={item.interpretation || ''} onChange={(event) => onChange(item.interpretation_id, 'interpretation', event.target.value)} /></label><div className="review-block-summary">{(item.content_blocks || []).map((block) => <span key={block.label}>{block.label} · {block.evidence_ids?.length || 0} 条证据</span>)}</div><div className="review-item-actions"><button className="review-small-button" onClick={() => onChange(item.interpretation_id, 'review_status', item.review_status === 'reviewed' ? 'reviewing' : 'reviewed')}><Check size={13} />{item.review_status === 'reviewed' ? '取消复核' : '标记已复核'}</button><button className="review-small-button" onClick={() => onChange(item.interpretation_id, 'human_lock', !item.human_lock)}>{item.human_lock ? <Lock size={13} /> : <ShieldCheck size={13} />}{item.human_lock ? '已锁定' : '锁定解读'}</button><button className="review-save" onClick={() => onSave(item)} disabled={busy}><Save size={13} />保存</button></div></div>
}

function App() {
  const [session, setSession] = useState(() => {
    const stored = readSession()
    if (runtimeConfig.apiConfigured) return stored?.mode === 'api' && stored.accessToken ? stored : null
    return stored || demoSession()
  })
  const [guestAccessError, setGuestAccessError] = useState('')
  const [guestRetry, setGuestRetry] = useState(0)
  const [query, setQuery] = useState('')
  const [activeTask, setActiveTask] = useState('case-001')
  const [activePage, setActivePage] = useState('task')
  const [activeTab, setActiveTab] = useState('概览')
  const [selectedEvidence, setSelectedEvidence] = useState('E-01')
  const [directoryOpen, setDirectoryOpen] = useState(true)
  const [railCollapsed, setRailCollapsed] = useState(false)
  const [evidenceItems, setEvidenceItems] = useState(initialEvidence)
  const [toast, setToast] = useState('')
  const [accessPanelOpen, setAccessPanelOpen] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [importMode, setImportMode] = useState('new')
  const [workbenchTasks, setWorkbenchTasks] = useState(tasks)
  const [pipelineTaskId, setPipelineTaskId] = useState(readCurrentTaskId)
  const [activeRegulationId, setActiveRegulationId] = useState(null)
  const [pipelineResult, setPipelineResult] = useState(null)
  const [pipelineBusy, setPipelineBusy] = useState(false)
  const [pipelineError, setPipelineError] = useState('')
  const [workflowState, setWorkflowState] = useState(null)
  const [reviewPanelOpen, setReviewPanelOpen] = useState(false)
  const [reviewState, setReviewState] = useState(null)
  const [lastReport, setLastReport] = useState(null)
  const fileInputRef = useRef(null)
  const s5ComparisonStatus = pipelineResult?.stages?.S5?.output?.comparison_status
  const s5Notice = s5ComparisonStatus === 'COMPLETED'
    ? ['新旧规比较已完成，变化结果待人工复核', '系统已完成条款级新增、删除、修改和数字变化识别；S5 不自动扩展为内部制度或整改结论。', 'S5 已完成']
    : s5ComparisonStatus === 'WAITING_RELATION_CONFIRMATION'
      ? ['旧规已登记，版本关系待确认', '两份原文和哈希已登记；完成有权人员确认后，系统才生成 S5 差异矩阵。', 'S5 待确认']
      : ['2017 年版新规已载入', '当前文件正文已登记；补充可核验旧规原文后，才进入 S5 版本比较。', '新规已载入']

  const filteredTasks = useMemo(
    () => workbenchTasks.filter((task) => task.title.includes(query) || task.institution.includes(query)),
    [query, workbenchTasks],
  )

  function notify(message) {
    setToast(message)
    window.setTimeout(() => setToast(''), 2400)
  }

  useEffect(() => {
    function handleAuthExpired() {
      window.localStorage.removeItem(SESSION_STORAGE_KEY)
      window.localStorage.removeItem(CURRENT_TASK_STORAGE_KEY)
      setSession(null)
      setWorkbenchTasks([])
      setPipelineTaskId(null)
      setActiveRegulationId(null)
      setPipelineResult(null)
      setWorkflowState(null)
      setReviewState(null)
      setAccessPanelOpen(false)
      setImportModalOpen(false)
      notify('公开工作空间已失效，正在重新创建匿名空间')
    }

    window.addEventListener('regulatory-workbench-auth-expired', handleAuthExpired)
    return () => window.removeEventListener('regulatory-workbench-auth-expired', handleAuthExpired)
  }, [])

  useEffect(() => {
    if (session?.mode !== 'api' || !session.accessToken) return undefined
    let cancelled = false
    async function hydrateRemoteWorkbench() {
      try {
        const [me, remoteTasks] = await Promise.all([
          apiClient.me(session.accessToken),
          apiClient.tasks(session.accessToken),
        ])
        if (cancelled) return
        void me
        setWorkbenchTasks(remoteTasks.map(mapApiTaskToWorkbenchTask))
        const currentTaskId = chooseCurrentTask(remoteTasks, readCurrentTaskId())
        if (!currentTaskId) {
          setPipelineTaskId(null)
          setActiveRegulationId(null)
          setPipelineResult(null)
          setWorkflowState(null)
          setReviewState(null)
          return
        }
        persistCurrentTaskId(currentTaskId)
        setActiveTask(currentTaskId)
        setPipelineTaskId(currentTaskId)
        const workflow = await apiClient.taskWorkflow(currentTaskId, session.accessToken).catch(() => null)
        if (cancelled || !workflow) return
        setWorkflowState(workflow)
        if (workflow.status !== 'completed') return
        const result = await apiClient.interpretation(currentTaskId, session.accessToken)
        if (cancelled) return
        setPipelineResult(result)
        setReviewState(result)
        setActiveRegulationId(result.task?.regulation_id || null)
      } catch {
        // The request layer retries cold-start failures; the UI keeps the last verified state if retries exhaust.
      }
    }
    hydrateRemoteWorkbench()
    return () => { cancelled = true }
  }, [session?.mode, session?.accessToken])

  useEffect(() => {
    if (!runtimeConfig.apiConfigured || session) return undefined
    let cancelled = false
    setGuestAccessError('')
    apiClient.guestSession()
      .then((auth) => apiClient.currentOrganization(auth.access_token).then((organization) => ({ auth, organization })))
      .then(({ auth, organization }) => {
        if (cancelled) return
        const nextSession = { mode: 'api', accessToken: auth.access_token, user: auth.user, organization }
        persistSession(nextSession)
        setSession(nextSession)
      })
      .catch((requestError) => {
        if (!cancelled) setGuestAccessError(requestError.message || '公开工作台暂时无法连接，请重试')
      })
    return () => { cancelled = true }
  }, [guestRetry, session])

  if (!session && runtimeConfig.apiConfigured) {
    return <PublicGuestLoading error={guestAccessError} onRetry={() => setGuestRetry((value) => value + 1)} />
  }

  function navigate(page) {
    setActivePage(page)
    if (page === 'interpretation') setActiveTab('概览')
    if (page === 'clause') setActiveTab('条款解读')
    if (page === 'compare') setActiveTab('版本比较')
  }

  function enterPreview() {
    const nextSession = demoSession()
    persistSession(nextSession)
    setSession(nextSession)
  }

  function logout() {
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
    window.localStorage.removeItem(CURRENT_TASK_STORAGE_KEY)
    setSession(null)
    setPipelineTaskId(null)
    setActiveRegulationId(null)
    setPipelineResult(null)
    setWorkflowState(null)
    setReviewState(null)
    setAccessPanelOpen(false)
  }

  function openImportModal(mode = 'new') {
    setImportMode(mode)
    setImportModalOpen(true)
  }

  function openPreviousVersionUpload() {
    const regulationId = activeRegulationId || pipelineResult?.task?.regulation_id
    if (!pipelineTaskId || !regulationId) {
      notify('请先载入当前法规并完成 S1—S4，再补充旧规原文')
      return
    }
    openImportModal('previous')
  }

  function handleEvidenceUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return
    const nextId = `E-${String(evidenceItems.length + 1).padStart(2, '0')}`
    setEvidenceItems((items) => [...items, {
      id: nextId,
      title: file.name,
      type: '用户上传证据',
      location: '本地文件 · 待解析',
      note: '文件已加入当前任务，解析和定位状态待处理。',
      tone: 'green',
    }])
    setSelectedEvidence(nextId)
    notify(`已添加证据：${file.name}`)
    event.target.value = ''
  }

  function handleRegulationImported(result) {
    const source = result.source_document
    const version = result.version
    const evidenceId = `REG-${source.document_id}`
    setEvidenceItems((items) => [{
      id: evidenceId,
      title: `${result.regulation.title} · ${version.version_label}`,
      type: '用户上传 PDF',
      location: `${source.file_name} · 第 1—${result.page_count} 页`,
      note: `已登记 ${result.article_count} 条款；原文定位已保存，可运行 S1—S4 解读。`,
      tone: 'green',
      sourceDocumentId: source.document_id,
      sourcePage: result.sample_articles?.[0]?.source_page || 1,
    }, ...items])
    setSelectedEvidence(evidenceId)
    setPipelineTaskId(result.task_id || null)
    setActiveTask(result.task_id || '')
    setActiveRegulationId(result.regulation?.regulation_id || null)
    persistCurrentTaskId(result.task_id)
    if (session?.accessToken) {
      apiClient.tasks(session.accessToken)
        .then((remoteTasks) => setWorkbenchTasks(remoteTasks.map(mapApiTaskToWorkbenchTask)))
        .catch(() => {})
    }
    setPipelineResult(null)
    setReviewState(null)
    setPipelineError('')
    setWorkflowState(null)
    notify(`已登记法规：${result.article_count} 条款可定位`)
    if (result.task_id) void runPipelineForTask(result.task_id)
  }

  async function monitorWorkflow(workflowId) {
    let latest = null
    for (let attempt = 0; attempt < 240; attempt += 1) {
      latest = await apiClient.workflow(workflowId, session?.accessToken)
      setWorkflowState(latest)
      if (['completed', 'failed', 'cancelled'].includes(latest.status)) return latest
      await new Promise((resolve) => window.setTimeout(resolve, 700))
    }
    throw new Error('工作流运行时间过长，请稍后在任务进度中继续查看')
  }

  async function loadWorkflowResult(taskId = pipelineTaskId) {
    const result = await apiClient.interpretation(taskId, session?.accessToken)
    setPipelineResult(result)
    setReviewState(result)
    setActiveRegulationId(result.task?.regulation_id || activeRegulationId)
    const evidence = (result.evidence || []).map((item) => ({
      id: item.evidence_id,
      title: `${item.locator?.article_no || '条款'} 原文证据`,
      type: '法规原文证据',
      location: `${item.source_text?.slice(0, 26) || '原文'} · 第${item.locator?.page || '待确认'}页`,
      note: item.description || '已绑定到 S1—S4 解读结果，待人工复核。',
      tone: 'green',
      sourceDocumentId: item.source_document_id,
      sourcePage: item.locator?.page || 1,
    }))
    setEvidenceItems((items) => [...evidence, ...items.filter((item) => !evidence.some((newItem) => newItem.id === item.id))])
    return result
  }

  async function runPipelineForTask(taskId) {
    if (!runtimeConfig.apiConfigured) {
      notify('当前公开预览未连接后端，私有部署配置 API 后才能运行 S1—S4')
      return
    }
    if (!taskId) {
      notify('请先上传法规，系统会自动创建解读任务')
      return
    }
    setPipelineBusy(true)
    setPipelineError('')
    try {
      const workflow = await apiClient.startWorkflow(taskId, { institution_type: '商业银行', business_scope: ['呆账核销'], region: '中国境内' }, session?.accessToken)
      setWorkflowState(workflow)
      const finished = workflow.status === 'completed' ? workflow : await monitorWorkflow(workflow.workflow_id)
      if (finished.status !== 'completed') throw new Error(finished.error_state?.message || '工作流运行失败，请查看失败节点并重试')
      const result = await loadWorkflowResult(taskId)
      const s5Status = result.stages?.S5?.output?.comparison_status
      notify(s5Status === 'COMPLETED' ? `Workflow 已完成，S1—S5 已完成，生成 ${result.requirements.length} 条监管要求` : `Workflow 已完成，生成 ${result.requirements.length} 条监管要求，S5 等待版本关系确认`)
    } catch (requestError) {
      setPipelineError(requestError.message || 'Workflow 运行失败')
      notify(requestError.message || 'Workflow 运行失败')
    } finally {
      setPipelineBusy(false)
    }
  }

  async function runPipeline() {
    await runPipelineForTask(pipelineTaskId)
  }

  async function retryWorkflow() {
    if (!workflowState?.workflow_id) return
    setPipelineBusy(true)
    setPipelineError('')
    try {
      const workflow = await apiClient.retryWorkflow(workflowState.workflow_id, session?.accessToken)
      setWorkflowState(workflow)
      const finished = workflow.status === 'completed' ? workflow : await monitorWorkflow(workflow.workflow_id)
      if (finished.status !== 'completed') throw new Error(finished.error_state?.message || '重试仍未完成')
      const result = await loadWorkflowResult()
      notify(`Workflow 重试完成，生成 ${result.requirements.length} 条监管要求`)
    } catch (requestError) { setPipelineError(requestError.message || 'Workflow 重试失败') } finally { setPipelineBusy(false) }
  }

  async function rerunWorkflowNode(nodeName) {
    if (!workflowState?.workflow_id) return
    setPipelineBusy(true)
    setPipelineError('')
    try {
      const workflow = await apiClient.rerunWorkflowNode(workflowState.workflow_id, nodeName, session?.accessToken)
      setWorkflowState(workflow)
      const finished = workflow.status === 'completed' ? workflow : await monitorWorkflow(workflow.workflow_id)
      if (finished.status !== 'completed') throw new Error(finished.error_state?.message || '节点重跑未完成')
      const result = await loadWorkflowResult()
      notify(`${nodeName} 节点重跑完成`)
      setPipelineResult(result)
    } catch (requestError) { setPipelineError(requestError.message || '节点重跑失败') } finally { setPipelineBusy(false) }
  }

  function handleEvidenceLocation(item) {
    setSelectedEvidence(item.id)
    if (item.sourceDocumentId && runtimeConfig.apiConfigured) {
      window.open(`${runtimeConfig.apiBaseUrl}/source-documents/${item.sourceDocumentId}/file#page=${item.sourcePage || 1}`, '_blank', 'noopener,noreferrer')
    }
    notify(`已定位：${item.location}`)
  }

  function openReviewPanel() {
    if (!pipelineTaskId) {
      notify('请先上传法规并运行 S1—S4')
      return
    }
    setReviewPanelOpen(true)
  }

  async function handleExport() {
    if (!pipelineTaskId || !runtimeConfig.apiConfigured) {
      notify('当前公开预览未连接后端，不能导出真实交付物')
      return
    }
    if (reviewState?.task?.task_status !== 'ready_for_export') {
      openReviewPanel()
      notify('请先完成人工复核并通过 QC')
      return
    }
    try {
      const report = await apiClient.exportDocx(pipelineTaskId, session?.accessToken)
      setLastReport(report)
      window.open(`${runtimeConfig.apiBaseUrl}${report.download_url}`, '_blank', 'noopener,noreferrer')
      if (report.html_download_url) window.open(`${runtimeConfig.apiBaseUrl}${report.html_download_url}`, '_blank', 'noopener,noreferrer')
      notify('HTML 与 Word 交付物已生成，并通过一致性检查')
    } catch (requestError) { notify(requestError.message || '导出失败') }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-stack">
            <img className="deloitte-logo" src={`${import.meta.env.BASE_URL}assets/deloitte-logo-white.png`} alt="Deloitte" />
            <span className="brand-name">外规解读智能体工作台</span>
          </div>
        </div>
        <div className="topbar-context">
          <div className="context-field">
            <span className="context-label">机构类型</span>
            <button className="select-button" onClick={() => notify('机构类型选择将在新建任务时生效')}>
              商业银行 <ChevronDown size={15} />
            </button>
          </div>
          <div className="top-status">
            <span className="context-label">任务状态</span>
            <StatusTag tone={reviewState?.task?.task_status === 'ready_for_export' ? 'green' : 'working'}>{reviewState?.task?.task_status || 'waiting_review'}</StatusTag>
          </div>
          <div className="top-status">
            <span className="context-label">质量检查</span>
            <StatusTag tone={reviewState?.task?.task_status === 'ready_for_export' ? 'green' : 'review'}>{reviewState?.task?.task_status === 'ready_for_export' ? '已通过' : '待复核'}</StatusTag>
          </div>
        </div>
        <div className="topbar-actions">
          <button className="outline-action" onClick={handleExport}>
            <FileText size={16} /> 导出 Word <ChevronDown size={14} />
          </button>
          <IconButton label="更多操作" onClick={() => notify('更多操作将在任务锁定后开放')}>
            <MoreVertical size={18} />
          </IconButton>
        </div>
      </header>

      <div className={`workspace-grid ${railCollapsed ? 'is-left-collapsed' : ''}`}>
        <aside className={`left-rail ${railCollapsed ? 'is-collapsed' : ''}`}>
          <div className="rail-tabs">
            <button className="rail-tab is-selected">任务列表</button>
          </div>

          <nav className="workspace-nav" aria-label="工作台页面">
            {[
              ['home', '首页', Home],
              ['task', '当前任务', FolderOpen],
              ['workflow', 'Workflow', Network],
              ['interpretation', '解读总览', BookOpen],
              ['clause', '条款解读', FileText],
              ['compare', '版本比较', ArrowRight],
              ['review', '人工审核', ClipboardCheck],
              ['reports', '报告中心', BarChart3],
            ].map(([page, label, Icon]) => <button key={page} className={`workspace-nav-item ${activePage === page ? 'is-active' : ''}`} onClick={() => navigate(page)}><Icon size={14} /><span>{label}</span></button>)}
          </nav>

          <div className="task-search">
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索任务标题" />
            <IconButton label="筛选任务" onClick={() => notify('当前筛选：全部任务')}><Filter size={16} /></IconButton>
          </div>

          <div className="task-list-header">
            <span>全部任务（{filteredTasks.length}）</span>
            <div className="task-list-header-actions"><button className="upload-regulation-button" onClick={() => openImportModal('new')}><FileUp size={13} /> 上传法规</button><button className="quiet-button" aria-label="任务排序" onClick={() => notify('任务排序：最近更新')}><SlidersHorizontal size={14} /></button></div>
          </div>

          <div className="task-list">
            {filteredTasks.map((task) => (
              <button
                className={`task-row ${activeTask === task.id ? 'is-active' : ''}`}
                key={task.id}
                onClick={() => { setActiveTask(task.id); navigate('task') }}
              >
                <span className={`task-dot ${task.state}`} />
                <span className="task-main">
                  <span className="task-title">{task.title}</span>
                  <span className="task-meta">{task.institution}　·　更新于 {task.updated}</span>
                </span>
                <span className={`task-status task-${task.state}`}>{task.status}</span>
              </button>
            ))}
            {filteredTasks.length === 0 && <div className="empty-search">没有匹配的任务</div>}
          </div>

          <div className="directory-heading">
            <span>法规目录</span>
            <button className="quiet-button" onClick={() => setDirectoryOpen((value) => !value)}>
              <ChevronDown className={directoryOpen ? '' : 'rotate-180'} size={16} />
            </button>
          </div>

          {directoryOpen && (
            <div className="directory-tree">
              <div className="tree-root"><ChevronDown size={14} /> 金融企业呆账核销管理办法</div>
              {toc.map((item) => (
                <div className="tree-section" key={item.label}>
                  <div className="tree-row"><ChevronRight size={14} /> {item.label}</div>
                  {item.open && item.children?.map((child, index) => (
                    <button className={`tree-child ${child === '核销程序' ? 'is-current' : ''}`} key={child} onClick={() => navigate('clause')}>
                      <span className={`tree-node ${index === 1 ? 'green' : ''}`} />{child}
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}

          <button className="collapse-rail" onClick={() => setRailCollapsed((value) => !value)}>
            {railCollapsed ? <ArrowRight size={16} /> : <ArrowLeft size={16} />} {railCollapsed ? '展开目录' : '收起目录'}
          </button>
        </aside>

        <main className="content-pane">
          {activePage === 'task' && (session?.mode !== 'api' || pipelineTaskId) ? <>
          <div className="content-toolbar">
            <div className="article-title-wrap">
              <span className="article-symbol">§</span>
              <div>
              <div className="eyebrow">法规解读任务 · 已载入用户提供文件</div>
                <h1>金融企业呆账核销管理办法（2017年版）</h1>
              </div>
            </div>
            <div className="content-toolbar-actions">
              <button className="run-pipeline-button" onClick={runPipeline} disabled={pipelineBusy}><Sparkles size={15} /> {pipelineBusy ? '正在运行 S1—S4…' : '运行 S1—S4'}</button>
              <button className="edit-button" onClick={openReviewPanel}><ClipboardCheck size={15} /> 人工复核</button>
            </div>
          </div>

          <div className="tab-bar" role="tablist" aria-label="解读内容标签">
            {['概览', '核心要求', '条款解读', '版本比较'].map((tab) => (
              <button className={`content-tab ${activeTab === tab ? 'is-active' : ''}`} key={tab} onClick={() => setActiveTab(tab)}>{tab}</button>
            ))}
          </div>

          <div className="content-scroll">
            <section className="notice-panel">
              <div className="notice-icon"><AlertCircle size={18} /></div>
              <div>
                <strong>{s5Notice[0]}</strong>
                <p>{s5Notice[1]}</p>
              </div>
              <StatusTag tone={s5ComparisonStatus === 'COMPLETED' ? 'review' : 'green'}>{s5Notice[2]}</StatusTag>
            </section>

            {pipelineError && <div className="pipeline-error"><AlertCircle size={15} />{pipelineError}</div>}
            {workflowState && <WorkflowProgress workflow={workflowState} onRetry={retryWorkflow} onRerun={rerunWorkflowNode} busy={pipelineBusy} />}
            {activeTab === '概览' && <Overview onEvidence={(id) => setSelectedEvidence(id)} pipelineResult={pipelineResult} onRun={runPipeline} pipelineBusy={pipelineBusy} />}
            {activeTab === '核心要求' && <CoreRequirements onEvidence={(id) => setSelectedEvidence(id)} pipelineResult={pipelineResult} />}
            {activeTab === '条款解读' && <ClauseInterpretation onEvidence={(id) => setSelectedEvidence(id)} pipelineResult={pipelineResult} />}
            {activeTab === '版本比较' && <CompareView onEvidence={(id) => setSelectedEvidence(id)} pipelineResult={pipelineResult} taskId={pipelineTaskId} session={session} onAddPrevious={openPreviousVersionUpload} onCompared={(stage) => setPipelineResult((current) => current ? { ...current, stages: { ...current.stages, S5: stage } } : current)} notify={notify} />}
          </div>
          </> : activePage === 'task' ? <div className="page-scroll"><div className="page-empty"><FileUp size={26} /><strong>当前匿名空间还没有任务</strong><span>上传一份法规原文后，系统会自动创建任务、解析 PDF 并运行 S1—S4。</span><button className="section-action" onClick={() => openImportModal('new')}>上传法规</button></div></div> : <div className="page-scroll">
            {activePage === 'home' && <HomePage onNavigate={navigate} pipelineResult={pipelineResult} workflowState={workflowState} reviewState={reviewState} />}
            {activePage === 'workflow' && <WorkflowPage workflow={workflowState} onRun={runPipeline} onRetry={retryWorkflow} onRerun={rerunWorkflowNode} busy={pipelineBusy} />}
            {activePage === 'interpretation' && <InterpretationPage pipelineResult={pipelineResult} onNavigate={navigate} onRun={runPipeline} pipelineBusy={pipelineBusy} />}
            {activePage === 'clause' && <ClausePage pipelineResult={pipelineResult} onEvidence={(id) => setSelectedEvidence(id)} />}
            {activePage === 'compare' && <ComparePage pipelineResult={pipelineResult} taskId={pipelineTaskId} session={session} onAddPrevious={openPreviousVersionUpload} onCompared={(stage) => setPipelineResult((current) => current ? { ...current, stages: { ...current.stages, S5: stage } } : current)} notify={notify} onEvidence={(id) => setSelectedEvidence(id)} />}
            {activePage === 'review' && <ReviewPage reviewState={reviewState} onOpen={openReviewPanel} onRun={runPipeline} />}
            {activePage === 'reports' && <ReportCenterPage reviewState={reviewState} lastReport={lastReport} onExport={handleExport} />}
          </div>}
        </main>

        <aside className="evidence-rail">
          <div className="evidence-header">
            <div className="evidence-title"><span className="evidence-bar" /> <h2>证据链</h2></div>
            <input ref={fileInputRef} className="hidden-file-input" type="file" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" onChange={handleEvidenceUpload} />
            <button className="add-evidence" onClick={() => fileInputRef.current?.click()}><Plus size={16} /> 添加证据</button>
          </div>
          <div className="evidence-intro">结论 → 解读 → 条款 → 原文件定位</div>
          <div className="evidence-list">
            {evidenceItems.map((item, index) => (
              <button className={`evidence-card ${selectedEvidence === item.id ? 'is-selected' : ''}`} key={item.id} onClick={() => setSelectedEvidence(item.id)}>
                <div className="evidence-card-top">
                  <span className={`evidence-number ${item.tone}`}>{index + 1}</span>
                  <span className="evidence-card-title">{item.title}</span>
                  <MoreVertical size={16} />
                </div>
                <div className="evidence-fields">
                  <div><span>来源类型</span><strong>{item.type}</strong></div>
                  <div><span>来源位置</span><strong>{item.location}</strong></div>
                  <div><span>说明</span><strong>{item.note}</strong></div>
                </div>
                <span className="evidence-link" onClick={(event) => { event.stopPropagation(); handleEvidenceLocation(item) }}>查看定位 <ExternalLink size={13} /></span>
              </button>
            ))}
          </div>
          <button className="all-evidence" onClick={() => notify(`共 ${evidenceItems.length} 条已登记证据，可点击卡片查看定位`)}>查看全部证据（{evidenceItems.length} 条） <ArrowRight size={16} /></button>
        </aside>
      </div>

      {toast && <div className="toast"><Check size={16} /> {toast}</div>}
      {accessPanelOpen && <AccessPanel session={session} onClose={() => setAccessPanelOpen(false)} onSessionChange={setSession} onLogout={logout} notify={notify} />}
      {importModalOpen && <RegulationImportModal session={session} taskId={importMode === 'previous' ? pipelineTaskId : null} regulationId={importMode === 'previous' ? (activeRegulationId || pipelineResult?.task?.regulation_id) : null} versionRole={importMode === 'previous' ? 'previous' : 'current'} onClose={() => setImportModalOpen(false)} onImported={handleRegulationImported} />}
      {reviewPanelOpen && <ReviewPanel session={session} taskId={pipelineTaskId} onClose={() => setReviewPanelOpen(false)} onReviewChanged={(nextReview) => { setReviewState(nextReview); setPipelineResult(nextReview) }} notify={notify} />}
    </div>
  )
}

function PublicGuestLoading({ error, onRetry }) {
  return <div className="auth-shell"><div className="auth-card"><div className="auth-brand"><img className="deloitte-logo" src={`${import.meta.env.BASE_URL}assets/deloitte-logo-white.png`} alt="Deloitte" /><span>外规解读智能体工作台</span></div><div className="auth-kicker">PUBLIC WORKSPACE</div><h1>{error ? '公开工作台连接失败' : '正在连接公开工作台…'}</h1><p className="auth-description">无需注册或登录，系统会自动为当前浏览器创建隔离的匿名工作空间。</p>{error ? <><div className="auth-error"><AlertCircle size={15} />{error}</div><button className="auth-submit" onClick={onRetry}>重新连接</button></> : <div className="auth-footer"><RefreshCw className="spin" size={14} />正在准备匿名工作空间</div>}</div></div>
}

function SectionTitle({ children, action }) {
  return <div className="section-title"><span className="section-bar" /><h2>{children}</h2>{action}</div>
}

function PageHeader({ eyebrow, title, description, action }) {
  return <div className="page-header"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>
}

function HomePage({ onNavigate, pipelineResult, workflowState, reviewState }) {
  const requirementCount = pipelineResult?.requirements?.length || 0
  const workflowLabel = workflowState?.status === 'completed' ? '已完成' : workflowState?.status === 'failed' ? '失败待处理' : workflowState ? '执行中' : '尚未启动'
  return <section className="page-content">
    <PageHeader eyebrow="工作台首页" title="外规解读工作台" description="从法规登记到证据绑定、人工复核和交付发布的统一入口。" action={<StatusTag tone={runtimeConfig.apiConfigured ? 'green' : 'review'}>{runtimeConfig.apiConfigured ? '已连接后端' : '前端预览'}</StatusTag>} />
    <div className="page-grid page-grid-three"><article className="metric-panel"><span>当前任务</span><strong>金融企业呆账核销管理办法</strong><small>2017 年版 · 商业银行</small><button className="link-button" onClick={() => onNavigate('task')}>进入任务 <ArrowRight size={13} /></button></article><article className="metric-panel"><span>Workflow</span><strong>{workflowState ? `${workflowState.progress}%` : '—'}</strong><small>{workflowLabel}{workflowState?.current_node ? ` · 当前 ${workflowState.current_node}` : ''}</small><button className="link-button" onClick={() => onNavigate('workflow')}>查看进度 <ArrowRight size={13} /></button></article><article className="metric-panel"><span>结构化要求</span><strong>{requirementCount || '待运行'}</strong><small>{requirementCount ? '已生成，等待人工复核' : '运行 Workflow 后生成'}</small><button className="link-button" onClick={() => onNavigate('interpretation')}>查看解读 <ArrowRight size={13} /></button></article></div>
    <div className="page-grid page-grid-two"><section className="page-panel"><div className="page-panel-head"><strong>当前任务状态</strong><StatusTag tone={reviewState?.task?.task_status === 'ready_for_export' ? 'green' : 'review'}>{reviewState?.task?.task_status || 'waiting_review'}</StatusTag></div><div className="page-detail-list"><div><span>法规来源</span><strong>用户提供 PDF · 2017 年版正文</strong></div><div><span>当前边界</span><strong>附件 1—3 和 2015 年旧规原文尚未核验</strong></div><div><span>发布条件</span><strong>人工复核、QC 和 Content Package 锁定</strong></div></div></section><section className="page-panel"><div className="page-panel-head"><strong>页面入口</strong><span className="eyebrow">保持三栏工作台结构</span></div><div className="page-entry-list">{[['workflow', 'Workflow', '查看节点状态、失败原因和重跑入口'], ['review', '人工审核', '逐项核验元数据、要求、解读和证据'], ['reports', '报告中心', '查看导出状态和 Word 交付物']].map(([page, label, note]) => <button key={page} onClick={() => onNavigate(page)}><strong>{label}</strong><span>{note}</span><ArrowRight size={14} /></button>)}</div></section></div>
  </section>
}

function WorkflowPage({ workflow, onRun, onRetry, onRerun, busy }) {
  return <section className="page-content"><PageHeader eyebrow="Workflow" title="任务执行流程" description="每个节点都保存状态和检查点；失败后可以重试或重跑指定节点。" action={<button className="run-pipeline-button" onClick={onRun} disabled={busy}>{busy ? '运行中…' : '启动 Workflow'} <Sparkles size={14} /></button>} />{workflow ? <WorkflowProgress workflow={workflow} onRetry={onRetry} onRerun={onRerun} busy={busy} /> : <div className="page-empty"><Network size={24} /><strong>当前任务尚未启动 Workflow</strong><span>启动后会依次执行 S1—S5，并在此显示实时进度。</span><button className="section-action" onClick={onRun}>启动任务</button></div>}<section className="page-panel"><div className="page-panel-head"><strong>节点说明</strong><span className="eyebrow">证据优先</span></div><div className="workflow-description-grid">{[['S1', '法规识别', '元数据、来源文件和待确认字段'], ['S2', '适用性与版本定位', '机构、业务、地域和版本关系'], ['S3', '条款拆解', '监管要求、规范词和数字表达'], ['S4', '整体与逐条解读', 'FACT、OFFICIAL、INTERPRETATION 内容块'], ['S5', '新旧规比较', '没有旧规时明确阻断，不生成差异结论']].map(([code, title, note]) => <div key={code}><strong>{code}</strong><span>{title}</span><small>{note}</small></div>)}</div></section></section>
}

function InterpretationPage({ pipelineResult, onNavigate, onRun, pipelineBusy }) {
  return <section className="page-content"><PageHeader eyebrow="解读总览" title="法规整体解读" description="整体结论以法规原文、适用性依据和条款结构化结果为基础。" action={<button className="link-button" onClick={() => onNavigate('clause')}>进入条款解读 <ArrowRight size={14} /></button>} /><Overview onEvidence={() => {}} pipelineResult={pipelineResult} onRun={onRun} pipelineBusy={pipelineBusy} /></section>
}

function ClausePage({ pipelineResult, onEvidence }) {
  return <section className="page-content"><PageHeader eyebrow="条款解读" title="逐条监管要求与解读" description="原文片段保持不变，监管要求、内容块和证据定位分开呈现。" /><ClauseInterpretation onEvidence={onEvidence} pipelineResult={pipelineResult} /></section>
}

function ComparePage({ pipelineResult, taskId, session, onAddPrevious, onCompared, notify, onEvidence }) {
  return <section className="page-content"><PageHeader eyebrow="版本比较" title="新旧规比较" description="只有旧规全文、版本关系和文件哈希均可核验时才生成差异结论。" /><CompareView onEvidence={onEvidence} pipelineResult={pipelineResult} taskId={taskId} session={session} onAddPrevious={onAddPrevious} onCompared={onCompared} notify={notify} /></section>
}

function ReviewPage({ reviewState, onOpen, onRun }) {
  const ready = reviewState?.task?.task_status === 'ready_for_export'
  return <section className="page-content"><PageHeader eyebrow="人工审核" title="人工复核与发布闸门" description="人工审核负责确认法规事实、证据定位和内容版本；系统不会替代审核责任。" action={<button className="edit-button page-dark-action" onClick={onOpen}><ClipboardCheck size={14} />打开审核工作台</button>} /><div className="page-grid page-grid-three"><article className="metric-panel"><span>任务状态</span><strong>{reviewState?.task?.task_status || '待运行'}</strong><small>{ready ? 'QC 已通过，可进入交付' : '尚未通过发布闸门'}</small></article><article className="metric-panel"><span>整体解读</span><strong>{reviewState?.overall?.review_status || '待生成'}</strong><small>{reviewState?.overall?.human_lock ? '已人工锁定' : '需要人工复核和锁定'}</small></article><article className="metric-panel"><span>证据链</span><strong>{reviewState?.evidence?.length ? `${reviewState.evidence.length} 条` : '待生成'}</strong><small>每条证据都需人工核验</small></article></div><div className="page-panel review-gate-panel"><div className="page-panel-head"><strong>审核操作</strong><span className="eyebrow">发布闸门</span></div><div className="page-detail-list"><div><span>第一步</span><strong>运行 Workflow 生成最新 S1—S5 结果</strong></div><div><span>第二步</span><strong>人工确认元数据、Requirement、Interpretation 和 Evidence</strong></div><div><span>第三步</span><strong>运行规则 QC，必要时运行 LLM Reviewer</strong></div><div><span>第四步</span><strong>生成锁定 Content Package 后发布</strong></div></div><div className="page-actions"><button className="run-pipeline-button" onClick={onRun}>运行 Workflow</button><button className="edit-button page-dark-action" onClick={onOpen}>打开人工审核</button></div></div></section>
}

function ReportCenterPage({ reviewState, lastReport, onExport }) {
  const exported = reviewState?.task?.task_status === 'exported' || reviewState?.task?.task_status === 'published'
  const ready = reviewState?.task?.task_status === 'ready_for_export' || exported
  const report = lastReport || reviewState?.task?.last_checkpoint?.report
  const reportReady = report?.consistency?.status === 'passed'
  const taskId = reviewState?.task?.task_id
  const wordUrl = report?.download_url || (report?.report_id && taskId ? `/api/tasks/${taskId}/exports/${report.report_id}` : null)
  const htmlUrl = report?.html_download_url || (report?.report_id && taskId ? `/api/tasks/${taskId}/exports/${report.report_id}/html` : null)
  const openDownload = (url) => { if (url) window.open(`${runtimeConfig.apiBaseUrl}${url}`, '_blank', 'noopener,noreferrer') }
  return <section className="page-content"><PageHeader eyebrow="报告中心" title="交付物与导出记录" description="HTML 页面和 Word 报告共享同一个锁定 Content Package。" action={<StatusTag tone={ready ? 'green' : 'review'}>{ready ? '可交付' : '待复核'}</StatusTag>} /><div className="page-panel report-hero"><FileText size={28} /><div><strong>外规解读报告</strong><p>{ready ? '当前任务已满足导出条件，可生成 HTML 和 Word 交付物。' : '完成人工复核、规则 QC 和 Content Package 锁定后才能导出。'}</p></div><button className="run-pipeline-button" onClick={onExport} disabled={!ready}>生成交付物</button></div><div className="page-grid page-grid-two"><section className="page-panel"><div className="page-panel-head"><strong>报告组成</strong></div><div className="report-section-list">{['法规概览与适用性判断', '监管要求与数字表达', '逐条解读与版本比较', 'Evidence 链路与真实性边界'].map((item, index) => <div key={item}><span>{String(index + 1).padStart(2, '0')}</span><strong>{item}</strong><StatusTag tone={ready ? 'green' : 'neutral'}>{ready ? '可导出' : '待复核'}</StatusTag></div>)}</div></section><section className="page-panel"><div className="page-panel-head"><strong>下载与一致性</strong>{reportReady && <StatusTag tone="green">检查通过</StatusTag>}</div><p className="page-body-note">{report ? `Package ${report.package_id || '—'} · SHA-256 ${String(report.content_hash || '').slice(0, 16)}…` : '生成后将在此显示 Content Package、文件下载和一致性结果。'}</p><div className="page-actions"><button className="outline-action" disabled={!wordUrl} onClick={() => openDownload(wordUrl)}><Download size={14} /> 下载 Word</button><button className="outline-action" disabled={!htmlUrl} onClick={() => openDownload(htmlUrl)}><ExternalLink size={14} /> 打开 HTML</button></div></section></div></section>
}

function WorkflowProgress({ workflow, onRetry, onRerun, busy }) {
  const labels = { S1: '法规识别', S2: '适用性与版本定位', S3: '条款拆解', S4: '整体与逐条解读', S5: '新旧规比较' }
  return <section className="workflow-progress-panel">
    <div className="workflow-progress-head"><div><span className="eyebrow">WORKFLOW ORCHESTRATOR</span><strong>{workflow.status === 'completed' ? 'Workflow 已完成' : workflow.status === 'failed' ? 'Workflow 失败' : 'Workflow 执行中'}</strong><small>{workflow.current_node ? `当前节点：${labels[workflow.current_node] || workflow.current_node}` : '已保存每个节点的检查点'}</small></div><div className="workflow-progress-number">{workflow.progress}%</div></div>
    <div className="workflow-progress-track"><span style={{ width: `${workflow.progress}%` }} /></div>
    <div className="workflow-node-list">{(workflow.nodes || []).map((node) => <div className={`workflow-node workflow-node-${node.status}`} key={node.node_id}><div className="workflow-node-main"><span className="workflow-node-dot" /><strong>{node.node_name}</strong><span>{labels[node.node_name] || node.node_name}</span></div><StatusTag tone={node.status === 'completed' || node.status === 'skipped' ? 'green' : node.status === 'failed' || node.status === 'blocked' ? 'review' : 'neutral'}>{node.status}</StatusTag>{node.status === 'failed' && <button className="link-button" onClick={() => onRerun(node.node_name)} disabled={busy}>重跑节点</button>}</div>)}</div>
    {workflow.status === 'failed' && <div className="workflow-failure"><AlertCircle size={14} />{workflow.error_state?.message || '节点执行失败'}<button className="review-small-button" onClick={onRetry} disabled={busy}>重试 Workflow</button></div>}
  </section>
}

function Overview({ onEvidence, pipelineResult, onRun, pipelineBusy }) {
  const applicability = pipelineResult?.stages?.S2?.output
  const requirements = pipelineResult?.stages?.S3?.output
  const s4 = pipelineResult?.stages?.S4?.output
  const s5 = pipelineResult?.stages?.S5?.output
  const locator = applicability?.regulation_locator
  const versionRelation = applicability?.version_relation
  const applicabilityLabel = { DIRECTLY_APPLICABLE: '直接适用', POTENTIALLY_APPLICABLE: '潜在适用', NOT_APPLICABLE: '不适用', NEEDS_REVIEW: '待确认' }[applicability?.status] || '待运行'
  const applicabilityTone = applicability?.status === 'DIRECTLY_APPLICABLE' ? 'green' : applicability?.status === 'NOT_APPLICABLE' ? 'neutral' : 'review'
  const s5Label = s5?.comparison_status === 'COMPLETED' ? '已完成比较' : s5?.comparison_status === 'WAITING_RELATION_CONFIRMATION' ? '版本关系待确认' : s5?.comparison_status === 'WAITING_SOURCE_VERIFICATION' ? '来源待核验' : s5 ? '待补充旧规' : '待运行'
  return (
    <>
      <section>
        <SectionTitle>法规概览</SectionTitle>
        <div className="data-table overview-table">
          <div className="data-cell label">法规名称</div><div className="data-cell value wide">金融企业呆账核销管理办法（2017年版）</div>
          <div className="data-cell label">发布机关</div><div className="data-cell value">财政部</div>
          <div className="data-cell label">文号</div><div className="data-cell value metadata-value-with-status"><span>财金〔2017〕90号</span><StatusTag tone="review">待人工确认</StatusTag></div>
          <div className="data-cell label">发布日期</div><div className="data-cell value">2017-08-31</div>
          <div className="data-cell label">生效日期</div><div className="data-cell value">2017-10-01</div>
          <div className="data-cell label">版本状态</div><div className="data-cell value"><StatusTag tone="green">已载入 4 页</StatusTag></div>
          <div className="data-cell label">适用范围</div><div className="data-cell value wide">金融企业；具体机构类型需结合正式原文和用户任务范围确认。</div>
          <div className="data-cell label">法规定位</div><div className="data-cell value wide"><StatusTag tone={locator?.status === 'IDENTIFIED' ? 'green' : 'review'}>{locator?.status === 'IDENTIFIED' ? '已定位' : locator ? '已定位但需复核' : '待运行'}</StatusTag>{locator ? ` · ${locator.source_file_name} · SHA-256 ${locator.source_hash.slice(0, 12)}…` : '尚未运行 S2 定位'}</div>
        </div>
      </section>

      <section>
        <SectionTitle>适用性判断</SectionTitle>
        <div className="data-table applicability-table">
          <div className="data-cell label">判断维度</div><div className="data-cell label">结论</div><div className="data-cell label">说明</div>
          <div className="data-cell">主体适用性</div><div className="data-cell"><StatusTag tone={applicabilityTone}>{applicabilityLabel}</StatusTag></div><div className="data-cell">{applicability?.reason || '基于当前文件正文初步判断；涉及附件和具体机构边界时需人工确认。'}</div>
          <div className="data-cell">地域适用性</div><div className="data-cell"><StatusTag tone={applicability?.matching_stage?.regional_temporal_match ? 'green' : 'review'}>{applicability?.matching_stage?.regional_temporal_match ? '初步适用' : '待确认'}</StatusTag></div><div className="data-cell">{applicability ? `当前任务地域：${applicability.region || '未指定'}。` : '当前文件明确面向中华人民共和国境内依法设立的金融企业。'}</div>
          <div className="data-cell">依据定位</div><div className="data-cell"><StatusTag tone={applicability?.applicability_evidence?.some((item) => item.status !== 'not_found') ? 'green' : 'review'}>{applicability?.applicability_evidence?.length ? `${applicability.applicability_evidence.length} 条定位` : '待运行'}</StatusTag></div><div className="data-cell">{applicability?.applicability_evidence?.[0]?.source_text || applicability?.applicability_evidence?.[0]?.reason || '适用性结论必须回溯法规原文定位。'}</div>
          <div className="data-cell">版本比较</div><div className="data-cell"><StatusTag tone={s5?.comparison_status === 'COMPLETED' ? 'green' : 'review'}>{s5Label}</StatusTag></div><div className="data-cell">{s5?.reason || '补充旧规原文并完成版本关系核验后，才生成条款级差异结论。'}</div>
          <div className="data-cell">版本关系</div><div className="data-cell"><StatusTag tone={versionRelation?.status === 'IDENTIFIED' ? 'green' : 'review'}>{versionRelation?.status === 'IDENTIFIED' ? '已登记前版' : versionRelation ? '候选关系待核验' : '待运行'}</StatusTag></div><div className="data-cell">{versionRelation?.reason || '当前尚未识别版本关系。'}</div>
        </div>
      </section>

      <section>
        <SectionTitle action={<button className="section-action" onClick={() => onEvidence('E-01')}>查看证据 <ExternalLink size={13} /></button>}>解读状态</SectionTitle>
        <div className="status-grid">
          <div className="status-card"><span>法规识别 · S1</span><strong>{pipelineResult ? '已完成' : '已定位'}</strong><StatusTag tone="green">{pipelineResult ? '元数据确认' : '来源登记完成'}</StatusTag></div>
          <div className="status-card"><span>适用性 · S2</span><strong>{applicabilityLabel}</strong><StatusTag tone={applicabilityTone}>{applicability?.confidence || '等待判断'}</StatusTag></div>
          <div className="status-card"><span>规则抽取 · S3</span><strong>{requirements ? `${requirements.requirement_count} 条` : '待解析'}</strong><StatusTag tone={requirements ? 'green' : 'review'}>{requirements ? '已结构化' : '下一节点'}</StatusTag></div>
          <div className="status-card"><span>条款解读 · S4</span><strong>{s4 ? `${s4.article_interpretation_count} 条` : '待生成'}</strong><StatusTag tone={s4 ? 'review' : 'neutral'}>{s4 ? '待人工复核' : '未运行'}</StatusTag></div>
          <div className="status-card"><span>版本比较</span><strong>{s5Label}</strong><StatusTag tone={s5?.comparison_status === 'COMPLETED' ? 'green' : 'review'}>{s5?.summary?.changed_article_count ? `${s5.summary.changed_article_count} 条变化` : '待核验'}</StatusTag></div>
          <div className="status-card"><span>流水线操作</span><strong>{pipelineResult ? '可复核' : '未运行'}</strong><button className="link-button" onClick={onRun} disabled={pipelineBusy}>{pipelineBusy ? '运行中…' : '运行 S1—S4'} <ArrowRight size={15} /></button></div>
        </div>
      </section>
    </>
  )
}

function CoreRequirements({ onEvidence, pipelineResult }) {
  if (pipelineResult) {
    const s3 = pipelineResult.stages?.S3?.output || {}
    return <section>
      <SectionTitle>核心要求（S3）</SectionTitle>
      <div className="pipeline-summary"><strong>已结构化 {pipelineResult.requirements.length} 条监管要求</strong><span>原子化动作：{pipelineResult.requirements.length} 条 · 数字表达：{s3.numeric_expression_count || 0} 个 · 规范词：{s3.normative_term_count || 0} 个</span>{s3.review_flags?.length > 0 && <small>复核提示：{s3.review_flags.join('；')}</small>}</div>
      <div className="requirement-list">
        {pipelineResult.requirements.slice(0, 24).map((requirement) => <button className="requirement-card" key={requirement.requirement_id} onClick={() => onEvidence(pipelineResult.evidence.find((item) => item.article_id === requirement.article_id)?.evidence_id)}>
          <div className="requirement-card-head"><span>{requirement.rule_type}</span><strong>{requirement.article_id}</strong><StatusTag tone="review">待复核</StatusTag></div>
          <p>{requirement.source_text}</p>
          <div className="requirement-grid"><span>主体</span><strong>{requirement.subject || '待确认'}</strong><span>行为/强度</span><strong>{[requirement.action, requirement.structured_data?.action_strength_level].filter(Boolean).join(' · ') || '未识别'}</strong><span>条件/例外</span><strong>{[requirement.condition, requirement.exception].filter(Boolean).join('；') || '未识别'}</strong><span>数字/时限</span><strong>{[requirement.deadline, requirement.frequency, requirement.threshold].filter(Boolean).join('；') || (requirement.structured_data?.numbers || []).map((item) => item.original_expression).join('、') || '未识别'}</strong></div>
        </button>)}
        {pipelineResult.requirements.length > 24 && <div className="pipeline-more">当前页面展示前 24 条；完整结果已保存在后端，可通过任务 API 查询。</div>}
      </div>
    </section>
  }
  return (
    <section>
      <SectionTitle>核心要求</SectionTitle>
      <div className="core-empty">
        <ShieldCheck size={30} />
        <h3>原文已载入，等待条款结构化</h3>
        <p>系统会从用户提供的 4 页 PDF 中提取第一条至第二十五条，再按责任主体、行为要求、条件、期限和证据位置生成核心要求。</p>
        <button className="link-button" onClick={() => onEvidence('E-01')}>查看当前来源登记 <ArrowRight size={15} /></button>
      </div>
    </section>
  )
}

function ClauseInterpretation({ onEvidence, pipelineResult }) {
  if (pipelineResult) {
    const articleInterpretations = pipelineResult.article_interpretations.slice(0, 12)
    const s4 = pipelineResult.stages?.S4?.output || {}
    const changeReady = s4.change_interpretation_status === 'GENERATED_NEEDS_REVIEW'
    return <section>
      <SectionTitle>条款解读（S4）</SectionTitle>
      <div className="pipeline-summary"><strong>整体解读已生成，当前状态：待人工复核</strong><span>{pipelineResult.overall.interpretation}</span><small>{changeReady ? `变化解读已生成 ${s4.change_interpretation_count || 0} 条，具体监管含义仍需人工复核。` : 'S5尚未形成可核验比较结果，本次未生成变化解读。'}</small></div>
      <div className="interpretation-list">
        {articleInterpretations.map((item) => <article className="interpretation-card" key={item.interpretation_id}>
          <div className="interpretation-card-head"><strong>{item.article_id}</strong><StatusTag tone="review">待人工复核</StatusTag></div>
          <h3>{item.summary}</h3>
          <p>{item.interpretation}</p>
          <div className="content-blocks">{item.content_blocks.map((block) => <div key={block.label} className={`content-block content-${block.label.toLowerCase()}`}><span>{block.label}</span><p>{block.text}</p></div>)}</div>
          <button className="link-button" onClick={() => onEvidence(item.content_blocks?.[0]?.evidence_ids?.[0])}>查看原文证据 <ExternalLink size={13} /></button>
        </article>)}
      </div>
    </section>
  }
  return (
    <section>
      <SectionTitle>条款解读</SectionTitle>
      <div className="clause-card">
        <div className="clause-label">当前任务状态</div>
        <h3>原文已载入，逐条解读待生成</h3>
        <p>本任务已登记法规名称、文号、发布日期、生效日期和用户提供 PDF。下一节点是条款拆解；涉及未提供的附件内容时，系统会停止并提示补充材料。</p>
        <div className="clause-footer"><StatusTag tone="green">新规已载入</StatusTag><button className="link-button" onClick={() => onEvidence('E-02')}>查看来源证据 <ExternalLink size={13} /></button></div>
      </div>
    </section>
  )
}

function CompareView({ onEvidence, pipelineResult, taskId, session, onAddPrevious, onCompared, notify }) {
  const [compareBusy, setCompareBusy] = useState(false)
  const [compareError, setCompareError] = useState('')
  const stage = pipelineResult?.stages?.S5
  const comparison = stage?.output
  const statusConfig = {
    COMPLETED: { label: '已完成比较', tone: 'green', note: '已完成条款级差异识别；变化的监管含义仍需人工复核。' },
    WAITING_RELATION_CONFIRMATION: { label: '版本关系待确认', tone: 'review', note: '已登记前一版本，但尚未完成有权人员确认。' },
    WAITING_SOURCE_VERIFICATION: { label: '来源待核验', tone: 'review', note: '两份版本的原文、哈希或条款结构尚未完整登记。' },
    SKIPPED_NO_PREVIOUS_SOURCE: { label: '待补充权威原文', tone: 'neutral', note: '未取得可核验的旧规全文，本任务不生成差异结论。' },
  }
  const currentStatus = statusConfig[comparison?.comparison_status] || statusConfig.SKIPPED_NO_PREVIOUS_SOURCE
  const changes = comparison?.changes || []
  const oldVersion = comparison?.old_version
  const newVersion = comparison?.new_version
  const changeLabels = { ADDED: '新增条款', DELETED: '删除条款', MODIFIED: '修改条款' }
  async function confirmAndCompare() {
    if (!taskId || !runtimeConfig.apiConfigured || session?.mode === 'preview') {
      notify('当前为公开预览，需连接真实后端后才能确认版本关系')
      return
    }
    setCompareBusy(true)
    setCompareError('')
    try {
      await apiClient.confirmS5Relation(taskId, { note: '页面人工确认版本关系' }, session.accessToken)
      const result = await apiClient.compareS5(taskId, session.accessToken)
      onCompared(result.stage)
      notify('S5 版本关系已确认并完成比较')
    } catch (requestError) {
      setCompareError(requestError.message || 'S5 比较失败')
    } finally {
      setCompareBusy(false)
    }
  }
  return (
    <section className="compare-page">
      <SectionTitle>新旧规比较（S5）</SectionTitle>
      <div className="compare-status-strip">
        <div>
          <span className="compare-status-label">当前比较状态</span>
          <strong>{currentStatus.label}</strong>
        </div>
        <StatusTag tone={currentStatus.tone}>{comparison?.summary?.changed_article_count ? `${comparison.summary.changed_article_count} 条变化` : currentStatus.note}</StatusTag>
      </div>
      <div className="compare-block">
        <div className="compare-head">
          <div><span>旧版本</span><strong>{oldVersion?.version_label || '金融企业呆账核销管理办法（2015年修订版）'}</strong><small>{oldVersion?.source_file_name ? `${oldVersion.source_file_name} · SHA-256 ${oldVersion.source_hash?.slice(0, 12)}…` : '文号：财金〔2015〕60号 · 原文未提供'}</small></div>
          <ArrowRight size={18} />
          <div><span>新版本</span><strong>{newVersion?.version_label || '金融企业呆账核销管理办法（2017年版）'}</strong><small>{newVersion?.source_file_name ? `${newVersion.source_file_name} · ${newVersion.article_count || 0} 条 · SHA-256 ${newVersion.source_hash?.slice(0, 12)}…` : '正文已载入 · 25 条 · 4 页'}</small></div>
        </div>
        {comparison?.comparison_status === 'COMPLETED' ? <div className="compare-results">
          <div className="compare-summary-grid">
            <div><span>新增</span><strong>{comparison.summary.counts.ADDED || 0}</strong></div>
            <div><span>删除</span><strong>{comparison.summary.counts.DELETED || 0}</strong></div>
            <div><span>修改</span><strong>{comparison.summary.counts.MODIFIED || 0}</strong></div>
            <div><span>未变化</span><strong>{comparison.unchanged_article_count || 0}</strong></div>
          </div>
          <div className="compare-change-list">
            {changes.map((change) => <article className="compare-change-card" key={change.change_id}>
              <div className="compare-change-head"><strong>{change.article_no} · {changeLabels[change.change_type] || change.change_type}</strong><StatusTag tone={change.change_type === 'MODIFIED' ? 'review' : 'neutral'}>{(change.change_dimensions || []).join(' / ')}</StatusTag></div>
              <div className="compare-evidence-columns">
                <div><span>旧规原文</span><p>{change.old_evidence?.source_text || '该条款为新规新增'}</p><small>{change.old_evidence ? `第 ${change.old_evidence.page || '待确认'} 页 · ${change.old_evidence.source_hash?.slice(0, 12)}…` : '无旧规定位'}</small></div>
                <div><span>新规原文</span><p>{change.new_evidence?.source_text || '该条款已从新规删除'}</p><small>{change.new_evidence ? `第 ${change.new_evidence.page || '待确认'} 页 · ${change.new_evidence.source_hash?.slice(0, 12)}…` : '无新规定位'}</small></div>
              </div>
            </article>)}
          </div>
          <p className="compare-boundary-note">{comparison.interpretation_note}</p>
        </div> : <div className="compare-blocked">
          <div className="compare-blocked-kicker">S5 / 版本关系与条款映射</div>
          <h3>{currentStatus.note}</h3>
          <p>{comparison?.reason || '系统已记录当前新规的版本信息，但尚未取得可核验的旧规全文。补齐旧规原文、文件哈希并完成版本关系核验后，才会进入条款映射和变化识别。'}</p>
          <div className="compare-requirements">
            <span><Check size={13} /> 新规正文已登记</span>
            <span><AlertCircle size={13} /> {comparison?.comparison_status === 'WAITING_RELATION_CONFIRMATION' ? '版本关系待确认' : '旧规全文待补充'}</span>
            <span><AlertCircle size={13} /> 变化结论未生成</span>
          </div>
          {comparison?.comparison_status === 'WAITING_RELATION_CONFIRMATION' && <button className="section-action" onClick={confirmAndCompare} disabled={compareBusy}>{compareBusy ? '正在比较…' : '确认版本关系并比较'}</button>}
          {(!comparison || comparison?.comparison_status === 'SKIPPED_NO_PREVIOUS_SOURCE') && <button className="section-action" onClick={onAddPrevious}>补充旧规原文</button>}
          {compareError && <div className="pipeline-error"><AlertCircle size={15} />{compareError}</div>}
          <button className="link-button" onClick={() => onEvidence('E-01')}>查看当前来源边界 <ExternalLink size={13} /></button>
        </div>}
      </div>
    </section>
  )
}

export default App
