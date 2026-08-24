import { useEffect, useState } from "react";
import { formatTaskDue } from "../dateUtils";
import DateTimePicker from "./DateTimePicker";

function TaskDetailsModal({ task, onClose, onDelete, onUpdate }) {
  const [mode, setMode] = useState("details");
  const [title, setTitle] = useState(task.title);
  const [dueAt, setDueAt] = useState(task.due_at ?? "");
  const [description, setDescription] = useState(task.description ?? "");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    function handleKeyDown(keyEvent) {
      if (keyEvent.key === "Escape" && !isSubmitting) {
        onClose();
      }
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isSubmitting, onClose]);

  function resetForm() {
    setTitle(task.title);
    setDueAt(task.due_at ?? "");
    setDescription(task.description ?? "");
    setErrorMessage("");
  }

  function startEditing() {
    resetForm();
    setMode("edit");
  }

  async function handleUpdate(submitEvent) {
    submitEvent.preventDefault();

    if (isSubmitting) {
      return;
    }

    if (!title.trim()) {
      setErrorMessage("タスクタイトルを入力してください");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      await onUpdate(task.id, {
        title: title.trim(),
        due_at: dueAt || null,
        description,
        completed: task.completed,
      });
      setMode("details");
    } catch (updateError) {
      setErrorMessage(updateError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage("");

    try {
      await onDelete(task.id);
    } catch (deleteError) {
      setErrorMessage(deleteError.message);
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(mouseEvent) => {
        if (
          mouseEvent.target === mouseEvent.currentTarget &&
          !isSubmitting
        ) {
          onClose();
        }
      }}
    >
      <section
        className="task-details-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="task-details-heading"
      >
        <div className="modal-header">
          <div>
            <p>タスク詳細</p>
            <h2 id="task-details-heading">
              {mode === "edit" ? "タスクを編集" : task.title}
            </h2>
          </div>
          <button
            className="modal-close-button"
            type="button"
            aria-label="閉じる"
            disabled={isSubmitting}
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {mode === "edit" ? (
          <form className="add-item-form task-edit-form" onSubmit={handleUpdate}>
            <div className="modal-form-field">
              <label htmlFor="edit-task-title">タスクタイトル</label>
              <input
                id="edit-task-title"
                type="text"
                value={title}
                autoFocus
                required
                onChange={(inputEvent) => setTitle(inputEvent.target.value)}
              />
            </div>

            <DateTimePicker
              defaultTime="23:45"
              id="edit-task-due-at"
              label="期限"
              optional
              value={dueAt}
              onChange={setDueAt}
            />

            <div className="modal-form-field">
              <label htmlFor="edit-task-description">
                説明 <span>任意</span>
              </label>
              <textarea
                id="edit-task-description"
                value={description}
                onChange={(inputEvent) =>
                  setDescription(inputEvent.target.value)
                }
              />
            </div>

            {errorMessage && (
              <p className="modal-error-message" role="alert">
                {errorMessage}
              </p>
            )}

            <div className="modal-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={isSubmitting}
                onClick={() => {
                  resetForm();
                  setMode("details");
                }}
              >
                キャンセル
              </button>
              <button
                className="primary-button"
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? "保存中..." : "保存"}
              </button>
            </div>
          </form>
        ) : mode === "delete" ? (
          <div className="delete-confirmation">
            <p>このタスクを削除しますか？</p>
            <p className="delete-confirmation-note">
              「{task.title}」は元に戻せません。
            </p>

            {errorMessage && (
              <p className="modal-error-message" role="alert">
                {errorMessage}
              </p>
            )}

            <div className="modal-actions">
              <button
                className="secondary-button"
                type="button"
                disabled={isSubmitting}
                onClick={() => {
                  setErrorMessage("");
                  setMode("details");
                }}
              >
                キャンセル
              </button>
              <button
                className="danger-button"
                type="button"
                disabled={isSubmitting}
                onClick={handleDelete}
              >
                {isSubmitting ? "削除中..." : "削除"}
              </button>
            </div>
          </div>
        ) : (
          <div className="task-details-content">
            <dl className="event-detail-list">
              <div>
                <dt>期限</dt>
                <dd>{formatTaskDue(task.due_at)}</dd>
              </div>
              <div>
                <dt>説明</dt>
                <dd className="event-detail-description">
                  {task.description || "未設定"}
                </dd>
              </div>
              <div>
                <dt>状態</dt>
                <dd>{task.completed ? "完了" : "未完了"}</dd>
              </div>
            </dl>

            {errorMessage && (
              <p className="modal-error-message" role="alert">
                {errorMessage}
              </p>
            )}

            <div className="modal-actions task-details-actions">
              <button
                className="danger-secondary-button"
                type="button"
                onClick={() => {
                  setErrorMessage("");
                  setMode("delete");
                }}
              >
                削除
              </button>
              <button
                className="primary-button"
                type="button"
                onClick={startEditing}
              >
                編集
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default TaskDetailsModal;
