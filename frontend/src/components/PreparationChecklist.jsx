import { useState } from "react";

function PreparationChecklist({
  eventId,
  preparations,
  onAdd,
  onDelete,
  onUpdate,
}) {
  const [newTitle, setNewTitle] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [busyAction, setBusyAction] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const isBusy = Boolean(busyAction);

  async function handleAdd(submitEvent) {
    submitEvent.preventDefault();
    const trimmedTitle = newTitle.trim();

    if (!trimmedTitle) {
      setErrorMessage("準備項目名を入力してください");
      return;
    }

    setBusyAction("add");
    setErrorMessage("");

    try {
      await onAdd(eventId, trimmedTitle);
      setNewTitle("");
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleToggle(preparation) {
    setBusyAction(`update-${preparation.id}`);
    setErrorMessage("");

    try {
      await onUpdate(eventId, preparation.id, {
        title: preparation.title,
        completed: !preparation.completed,
      });
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyAction("");
    }
  }

  function startEditing(preparation) {
    setEditingId(preparation.id);
    setEditingTitle(preparation.title);
    setErrorMessage("");
  }

  async function handleEdit(submitEvent, preparation) {
    submitEvent.preventDefault();
    const trimmedTitle = editingTitle.trim();

    if (!trimmedTitle) {
      setErrorMessage("準備項目名を入力してください");
      return;
    }

    setBusyAction(`update-${preparation.id}`);
    setErrorMessage("");

    try {
      await onUpdate(eventId, preparation.id, {
        title: trimmedTitle,
        completed: preparation.completed,
      });
      setEditingId(null);
      setEditingTitle("");
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyAction("");
    }
  }

  async function handleDelete(preparation) {
    setBusyAction(`delete-${preparation.id}`);
    setErrorMessage("");

    try {
      await onDelete(eventId, preparation.id);
      if (editingId === preparation.id) {
        setEditingId(null);
        setEditingTitle("");
      }
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyAction("");
    }
  }

  return (
    <section className="preparation-checklist" aria-labelledby="preparation-heading">
      <div className="preparation-heading">
        <div>
          <p>予定に必要なもの</p>
          <h3 id="preparation-heading">準備チェックリスト</h3>
        </div>
        {preparations && (
          <span>
            {preparations.filter((preparation) => !preparation.completed).length}
            件未完了
          </span>
        )}
      </div>

      {preparations === null ? (
        <p className="preparation-status-message" role="alert">
          準備項目を読み込めませんでした。
        </p>
      ) : preparations.length === 0 ? (
        <p className="preparation-status-message">準備項目はありません</p>
      ) : (
        <ul className="preparation-list">
          {preparations.map((preparation) => (
            <li
              className={preparation.completed ? "is-completed" : ""}
              key={preparation.id}
            >
              {editingId === preparation.id ? (
                <form
                  className="preparation-edit-form"
                  onSubmit={(submitEvent) =>
                    handleEdit(submitEvent, preparation)
                  }
                >
                  <input
                    type="text"
                    value={editingTitle}
                    aria-label="準備項目名"
                    autoFocus
                    disabled={isBusy}
                    onChange={(inputEvent) =>
                      setEditingTitle(inputEvent.target.value)
                    }
                  />
                  <button className="preparation-save-button" type="submit" disabled={isBusy}>
                    保存
                  </button>
                  <button
                    className="preparation-text-button"
                    type="button"
                    disabled={isBusy}
                    onClick={() => {
                      setEditingId(null);
                      setEditingTitle("");
                      setErrorMessage("");
                    }}
                  >
                    取消
                  </button>
                </form>
              ) : (
                <>
                  <label className="preparation-check-label">
                    <input
                      type="checkbox"
                      checked={preparation.completed}
                      disabled={isBusy}
                      onChange={() => handleToggle(preparation)}
                    />
                    <span>{preparation.title}</span>
                  </label>
                  <div className="preparation-item-actions">
                    <button
                      className="preparation-text-button"
                      type="button"
                      disabled={isBusy}
                      onClick={() => startEditing(preparation)}
                    >
                      編集
                    </button>
                    <button
                      className="preparation-delete-button"
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleDelete(preparation)}
                    >
                      削除
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {preparations !== null && (
        <form className="preparation-add-form" onSubmit={handleAdd}>
          <label htmlFor={`preparation-title-${eventId}`}>準備項目を追加</label>
          <div>
            <input
              id={`preparation-title-${eventId}`}
              type="text"
              value={newTitle}
              placeholder="例：PCを充電する"
              disabled={isBusy}
              onChange={(inputEvent) => setNewTitle(inputEvent.target.value)}
            />
            <button className="primary-button" type="submit" disabled={isBusy}>
              {busyAction === "add" ? "追加中..." : "追加"}
            </button>
          </div>
        </form>
      )}

      {errorMessage && (
        <p className="modal-error-message" role="alert">
          {errorMessage}
        </p>
      )}
    </section>
  );
}

export default PreparationChecklist;
