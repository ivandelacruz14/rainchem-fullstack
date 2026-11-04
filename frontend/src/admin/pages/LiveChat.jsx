import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import client from "../../api/client";
import { useAdminAuth } from "../../context/AdminAuthContext";
import ChatPane from "../live/ChatPane";
import ConversationList from "../live/ConversationList";
import CustomerPanel from "../live/CustomerPanel";

const LIST_POLL_MS = 5000;

export default function LiveChat() {
  const { admin } = useAdminAuth();
  const [params, setParams] = useSearchParams();
  const [rows, setRows] = useState(null);
  const [counts, setCounts] = useState({});
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("latest");
  const [search, setSearch] = useState("");
  const [openId, setOpenId] = useState(Number(params.get("conversation")) || null);
  const [view, setView] = useState(openId ? "chat" : "list"); // which pane shows on a phone

  const loadList = useCallback(() => {
    client.get("/api/admin/live-chat/conversations", { params: { filter, sort, search: search || undefined } })
      .then((res) => { setRows(res.data.conversations); setCounts(res.data.counts || {}); })
      .catch(() => setRows((prev) => prev || []));
  }, [filter, sort, search]);

  useEffect(() => {
    loadList();
    const timer = setInterval(() => { if (document.visibilityState !== "hidden") loadList(); }, LIST_POLL_MS);
    return () => clearInterval(timer);
  }, [loadList]);

  function open(id) {
    setOpenId(id);
    setView(id ? "chat" : "list");
    setParams(id ? { conversation: id } : {}, { replace: true });
  }

  const current = rows?.find((r) => r.id === openId) || (openId ? { id: openId, user: null, statusLabel: "", topicLabel: "" } : null);

  return (
    <div className="lc-page">
      <div className="admin-topbar">
        <div>
          <h1>Live Chat</h1>
          <p>Customers who contacted you. New messages appear within a few seconds.</p>
        </div>
      </div>

      <div className="lc-shell" data-view={view}>
        <div className="lc-col lc-col-list">
          <ConversationList
            rows={rows} counts={counts} filter={filter} onFilter={setFilter} search={search} onSearch={setSearch}
            sort={sort} onSort={setSort} openId={openId} onOpen={open}
          />
        </div>
        <div className="lc-col lc-col-chat">
          {current ? (
            <ChatPane
              key={current.id} conversation={current} canDeleteConversation={Boolean(admin?.isHead)}
              onBack={() => open(null)} onInfo={() => setView("info")} onChanged={loadList}
              onDeleted={() => { open(null); loadList(); }}
            />
          ) : (
            <div className="lc-empty"><strong>Select a conversation</strong><p>Choose a customer on the left to read and reply.</p></div>
          )}
        </div>
        <div className="lc-col lc-col-info">
          {current ? <CustomerPanel key={current.id} conversationId={current.id} onClose={() => setView("chat")} /> : null}
        </div>
      </div>
    </div>
  );
}
