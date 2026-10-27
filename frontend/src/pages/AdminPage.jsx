import React, { useEffect, useState } from "react";
import {
  Layout,
  Typography,
  Tabs,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Input,
  Space,
  Select,
  Switch,
  Modal,
  Popconfirm,
  Form,
  Empty,
  Spin,
  Alert,
  Divider,
  message,
  ConfigProvider,
} from "antd";
import {
  UserOutlined,
  FileTextOutlined,
  WarningOutlined,
  ProjectOutlined,
  ReloadOutlined,
  SearchOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import client from "../api/client";

const { Content } = Layout;
const { Title, Text } = Typography;
const { TextArea } = Input;

// 首页提取的品牌色
const BRAND_COLORS = {
  primaryBlue: "#1e3a8a",   // 首页深蓝色
  secondaryGreen: "#4c9141", // 首页森林绿
  lightBlue: "#3b82f6",     // 渐变过渡色
  bgGrey: "#f8fafc",        // 背景浅灰
};

export default function AdminPage() {
  const [tab, setTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // --- 逻辑与状态保持完全不变 ---
  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [contracts, setContracts] = useState([]);
  const [contractKeyword, setContractKeyword] = useState("");
  const [contractDetail, setContractDetail] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [templateClauses, setTemplateClauses] = useState([]);
  const [logs, setLogs] = useState([]);

  const [questionForm, setQuestionForm] = useState({
    clause_text: "",
    correct_answer: "risk",
    explanation: "",
    difficulty: "medium",
  });
  const [editingQuestionId, setEditingQuestionId] = useState(null);

  const [templateForm, setTemplateForm] = useState({
    category_key: "",
    category_label: "",
    title: "",
    content: "",
    tip: "",
    sort_order: 1,
    is_active: true,
  });
  const [editingTemplateId, setEditingTemplateId] = useState(null);
  const [notice, setNotice] = useState("");

  const isNotFoundLike = (err) => {
    const status = err?.response?.status;
    const msg = (err?.response?.data?.message || "").toLowerCase();
    return status === 404 || msg.includes("not found");
  };

  const loadOverview = async () => {
    try {
      const { data } = await client.get("/admin/overview");
      setOverview(data.data);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setOverview({
          stats: { users: 0, contracts: 0, risks: 0, jobs: 0 },
          contract_status: {},
          risk_level_dist: {},
          latest_contracts: [],
          latest_users: [],
        });
        setNotice("No overview data yet.");
        return;
      }
      throw err;
    }
  };

  const loadUsers = async () => {
    try {
      const { data } = await client.get("/admin/users?limit=200");
      setUsers(data.data?.items || []);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setUsers([]);
        setNotice("No users found.");
        return;
      }
      throw err;
    }
  };

  const loadContracts = async () => {
    const qs = new URLSearchParams({ limit: "100" });
    if (contractKeyword.trim()) qs.set("keyword", contractKeyword.trim());
    try {
      const { data } = await client.get(`/admin/contracts/search?${qs.toString()}`);
      setContracts(data.data?.items || []);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setContracts([]);
        setNotice("No contracts found.");
        return;
      }
      throw err;
    }
  };

  const loadQuestions = async () => {
    try {
      const { data } = await client.get("/admin/game-questions");
      setQuestions(data.data || []);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setQuestions([]);
        setNotice("No question bank data yet.");
        return;
      }
      throw err;
    }
  };

  const loadLogs = async () => {
    try {
      const { data } = await client.get("/admin/audit-logs?limit=200");
      setLogs(data.data?.items || []);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setLogs([]);
        setNotice("No audit logs yet.");
        return;
      }
      throw err;
    }
  };

  const loadTemplateClauses = async () => {
    try {
      const { data } = await client.get("/admin/template-clauses");
      setTemplateClauses(data.data || []);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setTemplateClauses([]);
        setNotice("No template clauses yet.");
        return;
      }
      throw err;
    }
  };

  const reloadCurrentTab = async (currentTab = tab) => {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      if (currentTab === "overview") await loadOverview();
      if (currentTab === "users") await loadUsers();
      if (currentTab === "contracts") await loadContracts();
      if (currentTab === "questions") await loadQuestions();
      if (currentTab === "templates") await loadTemplateClauses();
      if (currentTab === "logs") await loadLogs();
    } catch (err) {
      setError(err?.response?.data?.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reloadCurrentTab();
  }, [tab]);

  const toggleUserStatus = async (userId, enabled) => {
    await client.patch(`/admin/users/${userId}/status`, { enabled });
    message.success(`User status updated`);
    reloadCurrentTab("users");
    reloadCurrentTab("logs");
  };

  const deleteUser = async (userId) => {
    await client.delete(`/admin/users/${userId}`);
    message.success("User deleted");
    reloadCurrentTab("users");
    reloadCurrentTab("logs");
  };

  const openContractDetail = async (contractId) => {
    try {
      const { data } = await client.get(`/admin/contracts/${contractId}/detail`);
      setContractDetail(data.data);
    } catch (err) {
      if (isNotFoundLike(err)) {
        setContractDetail(null);
        setNotice("Contract detail not found.");
        return;
      }
      setError(err?.response?.data?.message || "Failed to load contract detail");
    }
  };

  const submitQuestion = async () => {
    if (!questionForm.clause_text.trim() || !questionForm.explanation.trim()) return;
    if (editingQuestionId) {
      await client.put(`/admin/game-questions/${editingQuestionId}`, questionForm);
      message.success("Question updated");
    } else {
      await client.post("/admin/game-questions", questionForm);
      message.success("Question created");
    }
    setEditingQuestionId(null);
    setQuestionForm({ clause_text: "", correct_answer: "risk", explanation: "", difficulty: "medium" });
    reloadCurrentTab("questions");
    reloadCurrentTab("logs");
  };

  const submitTemplateClause = async () => {
    if (!templateForm.category_key.trim() || !templateForm.title.trim()) return;
    const payload = { ...templateForm, sort_order: Number(templateForm.sort_order || 1) };
    if (editingTemplateId) {
      await client.put(`/admin/template-clauses/${editingTemplateId}`, payload);
      message.success("Template updated");
    } else {
      await client.post("/admin/template-clauses", payload);
      message.success("Template created");
    }
    setEditingTemplateId(null);
    setTemplateForm({ category_key: "", category_label: "", title: "", content: "", tip: "", sort_order: 1, is_active: true });
    reloadCurrentTab("templates");
    reloadCurrentTab("logs");
  };

  const stats = overview?.stats || {};

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: BRAND_COLORS.primaryBlue,
          borderRadius: 10,
          fontFamily: "'Inter', -apple-system, sans-serif",
        },
        components: {
          Button: {
            borderRadius: 24, // 同首页圆角
            fontWeight: 500,
          },
          Card: {
            boxShadow: "0 4px 20px rgba(0, 0, 0, 0.05)",
          },
          Tabs: {
            itemSelectedColor: BRAND_COLORS.primaryBlue,
            inkBarColor: BRAND_COLORS.primaryBlue,
          }
        },
      }}
    >
      <Layout style={{ minHeight: "100vh", background: BRAND_COLORS.bgGrey }}>
        {/* 背景 Hero Header - 呼应首页设计 */}
        <div style={{
          background: `linear-gradient(135deg, ${BRAND_COLORS.primaryBlue} 0%, ${BRAND_COLORS.lightBlue} 100%)`,
          padding: "40px 24px 100px 24px",
          color: "white"
        }}>
          <div style={{ maxWidth: 1200, margin: "0 auto", display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Title level={2} style={{ color: "white", margin: 0, fontWeight: 700 }}>Admin Console</Title>
              <Text style={{ color: "rgba(255,255,255,0.8)" }}>Secure infrastructure monitoring and content management</Text>
            </div>
            <Button
              ghost
              icon={<ReloadOutlined />}
              onClick={() => reloadCurrentTab()}
              loading={loading}
              style={{ color: 'white', borderColor: 'rgba(255,255,255,0.3)' }}
            >
              Refresh System
            </Button>
          </div>
        </div>

        <Content style={{ padding: "0 24px", maxWidth: 1240, margin: "-50px auto 0 auto", width: "100%" }}>
          {/* 导航 Tabs 卡片 */}
          <Card bordered={false} bodyStyle={{ padding: "0 24px" }} style={{ marginBottom: 20, borderRadius: 12 }}>
            <Tabs
              activeKey={tab}
              onChange={setTab}
              size="large"
              items={[
                { key: "overview", label: "Dashboard" },
                { key: "users", label: "Identity" },
                { key: "contracts", label: "Repository" },
                { key: "questions", label: "Game Bank" },
                { key: "templates", label: "Templates" },
                { key: "logs", label: "Security Logs" },
              ]}
            />
          </Card>

          {/* 全局通知 */}
          {error && <Alert message={error} type="error" showIcon closable style={{ marginBottom: 16, borderRadius: 10 }} />}
          {notice && <Alert message={notice} type="info" showIcon style={{ marginBottom: 16, borderRadius: 10 }} />}

          <Spin spinning={loading} tip="Syncing with server...">
            {/* Tab: Overview (Dashboard) */}
            {tab === "overview" && (
              <Space direction="vertical" size="large" style={{ display: "flex" }}>
                <Row gutter={[16, 16]}>
                  {[
                    { title: "Total Users", value: stats.users, icon: <UserOutlined />, color: BRAND_COLORS.primaryBlue },
                    { title: "Contracts", value: stats.contracts, icon: <FileTextOutlined />, color: BRAND_COLORS.lightBlue },
                    { title: "Identified Risks", value: stats.risks, icon: <WarningOutlined />, color: "#e11d48" },
                    { title: "AI Jobs", value: stats.jobs, icon: <ProjectOutlined />, color: BRAND_COLORS.secondaryGreen },
                  ].map((item, idx) => (
                    <Col span={6} key={idx}>
                      <Card bordered={false} hoverable>
                        <Statistic
                          title={<Text type="secondary">{item.title}</Text>}
                          value={item.value}
                          prefix={React.cloneElement(item.icon, { style: { color: item.color, marginRight: 8 } })}
                          valueStyle={{ fontWeight: 700, color: '#1e293b' }}
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="Contract Status" bordered={false} size="small">
                      <Space wrap>
                        {Object.entries(overview?.contract_status || {}).map(([k, v]) => (
                          <Tag color="processing" style={{ borderRadius: 20, padding: '2px 12px' }} key={k}>{k}: {v}</Tag>
                        ))}
                      </Space>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="Risk Distribution" bordered={false} size="small">
                      <Space wrap>
                        {Object.entries(overview?.risk_level_dist || {}).map(([k, v]) => (
                          <Tag color="volcano" style={{ borderRadius: 20, padding: '2px 12px' }} key={k}>{k}: {v}</Tag>
                        ))}
                      </Space>
                    </Card>
                  </Col>
                </Row>

                <Card title="Recent Activity - Users" bordered={false} size="small">
                  <Table
                    dataSource={overview?.latest_users}
                    pagination={false}
                    size="middle"
                    rowKey="id"
                    columns={[
                      { title: 'ID', dataIndex: 'id', width: 80, render: t => <Text code>{t}</Text> },
                      { title: 'User Name', dataIndex: 'name', render: t => <Text strong>{t}</Text> },
                      { title: 'Email Address', dataIndex: 'email' },
                      { title: 'Joined Date', dataIndex: 'created_at', render: t => <Text type="secondary">{t}</Text> },
                    ]}
                  />
                </Card>
              </Space>
            )}

            {/* Tab: Users (Identity) */}
            {tab === "users" && (
              <Card title="Identity & Access" bordered={false}>
                <Table
                  dataSource={users}
                  rowKey="id"
                  columns={[
                    { title: "ID", dataIndex: "id", width: 80 },
                    { title: "Name", dataIndex: "name", render: t => <Text strong>{t}</Text> },
                    { title: "Email", dataIndex: "email" },
                    {
                      title: "Role",
                      dataIndex: "is_admin",
                      render: (admin) => admin ? <Tag color="gold" icon={<CheckCircleOutlined />}>Admin</Tag> : <Tag>User</Tag>
                    },
                    {
                      title: "Status",
                      dataIndex: "is_active",
                      render: (active) => active ? <Tag color="green">Active</Tag> : <Tag color="red">Suspended</Tag>
                    },
                    { title: "Created At", dataIndex: "created_at", render: t => <Text type="secondary">{t}</Text> },
                    {
                      title: "Actions",
                      fixed: 'right',
                      render: (_, record) => !record.is_admin && (
                        <Space>
                          <Button
                            size="small"
                            shape="round"
                            onClick={() => toggleUserStatus(record.id, !record.is_active)}
                          >
                            {record.is_active ? "Suspend" : "Activate"}
                          </Button>
                          <Popconfirm title="Permanent Delete?" onConfirm={() => deleteUser(record.id)} okText="Delete" cancelText="Cancel" okButtonProps={{danger: true}}>
                            <Button size="small" shape="circle" danger icon={<DeleteOutlined />} />
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Card>
            )}

            {/* Tab: Contracts (Repository) */}
            {tab === "contracts" && (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card bordered={false} bodyStyle={{ padding: 16 }}>
                  <Space>
                    <Input
                      placeholder="Search title, owner, or email..."
                      value={contractKeyword}
                      onChange={e => setContractKeyword(e.target.value)}
                      style={{ width: 350, borderRadius: 20 }}
                      prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
                    />
                    <Button type="primary" onClick={() => reloadCurrentTab("contracts")}>Search Database</Button>
                  </Space>
                </Card>
                <Table
                  dataSource={contracts}
                  rowKey="id"
                  columns={[
                    { title: "Title", dataIndex: "title", render: t => <Text strong>{t}</Text> },
                    { title: "Status", dataIndex: "status", render: (s) => <Tag color={s === 'Completed' ? 'green' : 'blue'}>{s}</Tag> },
                    { title: "Category", dataIndex: "contract_type" },
                    { title: "Owner", render: (_, r) => <Text type="secondary">{r.user_email || r.user_id}</Text> },
                    { title: "Upload Date", dataIndex: "created_at" },
                    {
                      title: "Action",
                      render: (_, r) => <Button type="link" onClick={() => openContractDetail(r.id)}>View Analysis</Button>
                    }
                  ]}
                />

                <Modal
                  title={<Title level={4}>Analysis Report: {contractDetail?.contract.title}</Title>}
                  open={!!contractDetail}
                  onCancel={() => setContractDetail(null)}
                  footer={[<Button key="close" shape="round" onClick={() => setContractDetail(null)}>Close Report</Button>]}
                  width={900}
                >
                  {contractDetail && (
                    <div style={{ maxHeight: '65vh', overflowY: 'auto', paddingRight: 8 }}>
                      <Row gutter={16} style={{ marginBottom: 20 }}>
                        <Col span={12}><Card size="small" title="Status"><Tag color="blue">{contractDetail.contract.status}</Tag></Card></Col>
                        <Col span={12}><Card size="small" title="Risks Count"><Text icon={<WarningOutlined />} danger strong>{contractDetail.risks?.length || 0} Issues</Text></Card></Col>
                      </Row>
                      <Divider orientation="left">Metadata Extracts</Divider>
                      <pre style={{ background: '#f8fafc', padding: 16, borderRadius: 12, border: '1px solid #e2e8f0' }}>
                        {JSON.stringify(contractDetail.contract.key_info || {}, null, 2)}
                      </pre>
                      <Divider orientation="left">Critical Risks</Divider>
                      <Table
                         size="small"
                         dataSource={contractDetail.risks}
                         pagination={{ pageSize: 5 }}
                         columns={[
                           { title: 'Level', dataIndex: 'risk_level', render: l => <Tag color={l==='High'?'red':'orange'}>{l}</Tag> },
                           { title: 'Risk Category', dataIndex: 'risk_type', strong: true },
                           { title: 'Evidence from Text', dataIndex: 'evidence_sentence', italic: true }
                         ]}
                      />
                    </div>
                  )}
                </Modal>
              </Space>
            )}

            {/* Tab: Question Bank (Game Bank) */}
            {tab === "questions" && (
              <Row gutter={20}>
                <Col span={9}>
                  <Card title={<Space><PlusOutlined />{editingQuestionId ? "Update Question" : "New Question"}</Space>} bordered={false}>
                    <Form layout="vertical">
                      <Form.Item label="Clause/Text Snippet" required>
                        <TextArea rows={4} placeholder="Paste the contract clause here..." value={questionForm.clause_text} onChange={e => setQuestionForm({...questionForm, clause_text: e.target.value})} />
                      </Form.Item>
                      <Form.Item label="Expert Explanation" required>
                        <TextArea rows={3} placeholder="Explain why this is a risk/safe..." value={questionForm.explanation} onChange={e => setQuestionForm({...questionForm, explanation: e.target.value})} />
                      </Form.Item>
                      <Row gutter={16}>
                        <Col span={12}>
                          <Form.Item label="Truth">
                            <Select value={questionForm.correct_answer} onChange={v => setQuestionForm({...questionForm, correct_answer: v})}>
                              <Select.Option value="risk">Risk</Select.Option>
                              <Select.Option value="safe">Safe</Select.Option>
                            </Select>
                          </Form.Item>
                        </Col>
                        <Col span={12}>
                          <Form.Item label="Difficulty">
                            <Select value={questionForm.difficulty} onChange={v => setQuestionForm({...questionForm, difficulty: v})}>
                              <Select.Option value="easy">Easy</Select.Option>
                              <Select.Option value="medium">Medium</Select.Option>
                              <Select.Option value="hard">Hard</Select.Option>
                            </Select>
                          </Form.Item>
                        </Col>
                      </Row>
                      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                        {editingQuestionId && <Button onClick={() => setEditingQuestionId(null)}>Cancel</Button>}
                        <Button type="primary" onClick={submitQuestion}>{editingQuestionId ? "Update Entry" : "Save to Bank"}</Button>
                      </Space>
                    </Form>
                  </Card>
                </Col>
                <Col span={15}>
                  <Card title="Active Question Bank" bordered={false}>
                    <Table
                      dataSource={questions}
                      rowKey="id"
                      size="small"
                      columns={[
                        { title: "Level", dataIndex: "difficulty", render: d => <Tag>{d.toUpperCase()}</Tag> },
                        { title: "Truth", dataIndex: "correct_answer", render: a => <Tag color={a==='risk'?'red':'green'}>{a.toUpperCase()}</Tag> },
                        { title: "Snippet", dataIndex: "clause_text", ellipsis: true },
                        {
                          title: "Actions",
                          render: (_, r) => (
                            <Space>
                              <Button size="small" type="text" icon={<EditOutlined />} onClick={() => {
                                setEditingQuestionId(r.id);
                                setQuestionForm({ ...r });
                              }} />
                              <Popconfirm title="Delete entry?" onConfirm={() => deleteUser(r.id)}>
                                <Button size="small" type="text" danger icon={<DeleteOutlined />} />
                              </Popconfirm>
                            </Space>
                          )
                        }
                      ]}
                    />
                  </Card>
                </Col>
              </Row>
            )}

            {/* Tab: Templates */}
            {tab === "templates" && (
               <Row gutter={20}>
                 <Col span={9}>
                  <Card title={editingTemplateId ? "Update Template" : "New Library Entry"} bordered={false}>
                     <Form layout="vertical">
                        <Form.Item label="Classification" required>
                          <Space.Compact style={{ width: '100%' }}>
                            <Input placeholder="Key (e.g. pay)" value={templateForm.category_key} onChange={e => setTemplateForm({...templateForm, category_key: e.target.value})} />
                            <Input placeholder="Label (e.g. Salary)" value={templateForm.category_label} onChange={e => setTemplateForm({...templateForm, category_label: e.target.value})} />
                          </Space.Compact>
                        </Form.Item>
                        <Form.Item label="Clause Title" required>
                          <Input value={templateForm.title} onChange={e => setTemplateForm({...templateForm, title: e.target.value})} />
                        </Form.Item>
                        <Form.Item label="Standard Content" required>
                          <TextArea rows={5} value={templateForm.content} onChange={e => setTemplateForm({...templateForm, content: e.target.value})} />
                        </Form.Item>
                        <Form.Item label="Legal Tip">
                          <TextArea rows={2} value={templateForm.tip} onChange={e => setTemplateForm({...templateForm, tip: e.target.value})} />
                        </Form.Item>
                        <Form.Item>
                           <Space size="large">
                             <Space>Order: <Input type="number" style={{ width: 70 }} value={templateForm.sort_order} onChange={e => setTemplateForm({...templateForm, sort_order: e.target.value})} /></Space>
                             <Switch checked={templateForm.is_active} onChange={v => setTemplateForm({...templateForm, is_active: v})} /> <Text>Visible to Users</Text>
                           </Space>
                        </Form.Item>
                        <Button type="primary" block style={{ background: BRAND_COLORS.secondaryGreen }} onClick={submitTemplateClause}>
                          {editingTemplateId ? "Update Entry" : "Publish to Library"}
                        </Button>
                     </Form>
                  </Card>
                 </Col>
                 <Col span={15}>
                  <Card title="Clause Library" bordered={false}>
                     <Table
                      dataSource={templateClauses}
                      rowKey="id"
                      size="small"
                      columns={[
                        { title: 'Category', dataIndex: 'category_label', render: t => <Tag>{t}</Tag> },
                        { title: 'Title', dataIndex: 'title', strong: true },
                        { title: 'Visible', dataIndex: 'is_active', render: a => a ? <Text type="success">Yes</Text> : <Text type="danger">No</Text> },
                        { title: 'Actions', render: (_, r) => (
                          <Space>
                             <Button size="small" type="link" onClick={() => { setEditingTemplateId(r.id); setTemplateForm({...r}); }}>Edit</Button>
                             <Popconfirm title="Delete template?"><Button size="small" type="link" danger>Delete</Button></Popconfirm>
                          </Space>
                        )}
                      ]}
                     />
                  </Card>
                 </Col>
               </Row>
            )}

            {/* Tab: Security Logs */}
            {tab === "logs" && (
              <Card title="System Audit Logs" bordered={false}>
                <Table
                  dataSource={logs}
                  rowKey="id"
                  size="middle"
                  columns={[
                    { title: "Timestamp", dataIndex: "created_at", width: 180, render: t => <Text type="secondary">{t}</Text> },
                    { title: "Operator", dataIndex: "admin_email", render: t => <Text strong>{t}</Text> },
                    { title: "Operation", dataIndex: "action", render: a => <Tag color="blue">{a}</Tag> },
                    { title: "Target", render: (_, r) => <Tag>{r.target_type}</Tag> },
                    { title: "Summary", dataIndex: "summary", ellipsis: true },
                  ]}
                />
              </Card>
            )}
          </Spin>
        </Content>

        <footer style={{ textAlign: 'center', padding: '24px', color: '#94a3b8' }}>
          ContractGuard Admin Interface &copy; 2026 Internal Security System
        </footer>
      </Layout>
    </ConfigProvider>
  );
}