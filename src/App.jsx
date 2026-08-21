import { useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Bell,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  ExternalLink,
  FileText,
  Filter,
  FolderOpen,
  MoreVertical,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  X,
} from 'lucide-react'

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

function App() {
  const [query, setQuery] = useState('')
  const [activeTask, setActiveTask] = useState('case-001')
  const [activeTab, setActiveTab] = useState('概览')
  const [selectedEvidence, setSelectedEvidence] = useState('E-01')
  const [directoryOpen, setDirectoryOpen] = useState(true)
  const [railCollapsed, setRailCollapsed] = useState(false)
  const [evidenceItems, setEvidenceItems] = useState(initialEvidence)
  const [toast, setToast] = useState('')
  const fileInputRef = useRef(null)

  const filteredTasks = useMemo(
    () => tasks.filter((task) => task.title.includes(query) || task.institution.includes(query)),
    [query],
  )

  function notify(message) {
    setToast(message)
    window.setTimeout(() => setToast(''), 2400)
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

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-stack">
            <img className="deloitte-logo" src="/assets/deloitte-logo-white.png" alt="Deloitte" />
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
            <StatusTag tone="working">处理中</StatusTag>
          </div>
          <div className="top-status">
            <span className="context-label">质量检查</span>
            <StatusTag tone="review">待确认</StatusTag>
          </div>
        </div>
        <div className="topbar-actions">
          <button className="outline-action" onClick={() => notify('报告尚未锁定，暂不能导出 Word')}>
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

          <div className="task-search">
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索任务标题" />
            <IconButton label="筛选任务" onClick={() => notify('当前筛选：全部任务')}><Filter size={16} /></IconButton>
          </div>

          <div className="task-list-header">
            <span>全部任务（{filteredTasks.length}）</span>
            <button className="quiet-button" onClick={() => notify('任务排序：最近更新')}><SlidersHorizontal size={14} /></button>
          </div>

          <div className="task-list">
            {filteredTasks.map((task) => (
              <button
                className={`task-row ${activeTask === task.id ? 'is-active' : ''}`}
                key={task.id}
                onClick={() => setActiveTask(task.id)}
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
                    <button className={`tree-child ${child === '核销程序' ? 'is-current' : ''}`} key={child} onClick={() => setActiveTab('条款解读')}>
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
          <div className="content-toolbar">
            <div className="article-title-wrap">
              <span className="article-symbol">§</span>
              <div>
              <div className="eyebrow">法规解读任务 · 已载入用户提供文件</div>
                <h1>金融企业呆账核销管理办法（2017年版）</h1>
              </div>
            </div>
            <button className="edit-button" onClick={() => notify('元数据编辑将在任务创建流程中开放')}><Pencil size={15} /> 编辑元数据</button>
          </div>

          <div className="tab-bar" role="tablist" aria-label="解读内容标签">
            {['概览', '核心要求', '条款解读'].map((tab) => (
              <button className={`content-tab ${activeTab === tab ? 'is-active' : ''}`} key={tab} onClick={() => setActiveTab(tab)}>{tab}</button>
            ))}
          </div>

          <div className="content-scroll">
            <section className="notice-panel">
              <div className="notice-icon"><AlertCircle size={18} /></div>
              <div>
                <strong>2017 年版新规已载入，本任务暂不启用 S5</strong>
                <p>当前文件正文覆盖第一条至第二十五条；附件未包含在本次 PDF 中，涉及附件时会明确提示并停止生成结论。</p>
              </div>
              <StatusTag tone="green">新规已载入</StatusTag>
            </section>

            {activeTab === '概览' && <Overview onEvidence={(id) => setSelectedEvidence(id)} />}
            {activeTab === '核心要求' && <CoreRequirements onEvidence={(id) => setSelectedEvidence(id)} />}
            {activeTab === '条款解读' && <ClauseInterpretation onEvidence={(id) => setSelectedEvidence(id)} />}
          </div>
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
                <span className="evidence-link" onClick={(event) => { event.stopPropagation(); setSelectedEvidence(item.id); notify(`已定位：${item.location}`) }}>查看定位 <ExternalLink size={13} /></span>
              </button>
            ))}
          </div>
          <button className="all-evidence" onClick={() => notify(`共 ${evidenceItems.length} 条已登记证据，可点击卡片查看定位`)}>查看全部证据（{evidenceItems.length} 条） <ArrowRight size={16} /></button>
        </aside>
      </div>

      {toast && <div className="toast"><Check size={16} /> {toast}</div>}
    </div>
  )
}

function SectionTitle({ children, action }) {
  return <div className="section-title"><span className="section-bar" /><h2>{children}</h2>{action}</div>
}

function Overview({ onEvidence }) {
  return (
    <>
      <section>
        <SectionTitle>法规概览</SectionTitle>
        <div className="data-table overview-table">
          <div className="data-cell label">法规名称</div><div className="data-cell value wide">金融企业呆账核销管理办法（2017年版）</div>
          <div className="data-cell label">发布机关</div><div className="data-cell value">财政部</div>
          <div className="data-cell label">文号</div><div className="data-cell value">财金〔2017〕90号</div>
          <div className="data-cell label">发布日期</div><div className="data-cell value">2017-08-31</div>
          <div className="data-cell label">生效日期</div><div className="data-cell value">2017-10-01</div>
          <div className="data-cell label">版本状态</div><div className="data-cell value"><StatusTag tone="green">已载入 4 页</StatusTag></div>
          <div className="data-cell label">适用范围</div><div className="data-cell value wide">金融企业；具体机构类型需结合正式原文和用户任务范围确认。</div>
        </div>
      </section>

      <section>
        <SectionTitle>适用性判断</SectionTitle>
        <div className="data-table applicability-table">
          <div className="data-cell label">判断维度</div><div className="data-cell label">结论</div><div className="data-cell label">说明</div>
          <div className="data-cell">主体适用性</div><div className="data-cell"><StatusTag tone="review">待确认</StatusTag></div><div className="data-cell">基于当前文件正文初步判断；涉及附件和具体机构边界时需人工确认。</div>
          <div className="data-cell">地域适用性</div><div className="data-cell"><StatusTag tone="green">初步适用</StatusTag></div><div className="data-cell">当前文件明确面向中华人民共和国境内依法设立的金融企业。</div>
          <div className="data-cell">版本比较</div><div className="data-cell"><StatusTag tone="neutral">暂不启用</StatusTag></div><div className="data-cell">用户未提供 2015 年版，本任务不执行 S5。</div>
        </div>
      </section>

      <section>
        <SectionTitle action={<button className="section-action" onClick={() => onEvidence('E-01')}>查看证据 <ExternalLink size={13} /></button>}>解读状态</SectionTitle>
        <div className="status-grid">
          <div className="status-card"><span>法规识别</span><strong>已定位</strong><StatusTag tone="green">来源登记完成</StatusTag></div>
          <div className="status-card"><span>条款拆解</span><strong>待解析</strong><StatusTag tone="review">下一节点</StatusTag></div>
          <div className="status-card"><span>版本比较</span><strong>暂不启用</strong><StatusTag tone="neutral">本任务跳过</StatusTag></div>
          <div className="status-card"><span>质量检查</span><strong>待确认</strong><StatusTag tone="review">不可发布</StatusTag></div>
        </div>
      </section>
    </>
  )
}

function CoreRequirements({ onEvidence }) {
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

function ClauseInterpretation({ onEvidence }) {
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

export default App
