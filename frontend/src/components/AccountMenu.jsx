import { useEffect, useRef, useState } from "react";

function getUserInitial(user) {
  const label = user.displayName?.trim() || user.email?.trim() || "U";
  return label.charAt(0).toUpperCase();
}

function AccountMenu({ onLogout, user }) {
  const [isOpen, setIsOpen] = useState(false);
  const [failedPhotoUrl, setFailedPhotoUrl] = useState("");
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!menuRef.current?.contains(event.target)) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  function handleLogout() {
    setIsOpen(false);
    onLogout();
  }

  const shouldShowPhoto =
    user.photoURL && user.photoURL !== failedPhotoUrl;

  return (
    <div className="account-menu" ref={menuRef}>
      <button
        ref={triggerRef}
        className="account-menu-trigger"
        type="button"
        aria-controls="account-menu-popover"
        aria-expanded={isOpen}
        aria-label="アカウントメニューを開く"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
      >
        {shouldShowPhoto ? (
          <img
            className="account-avatar"
            src={user.photoURL}
            alt=""
            referrerPolicy="no-referrer"
            onError={() => setFailedPhotoUrl(user.photoURL)}
          />
        ) : (
          <span className="account-avatar-fallback" aria-hidden="true">
            {getUserInitial(user)}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          id="account-menu-popover"
          className="account-menu-popover"
          role="dialog"
          aria-label="アカウント情報"
        >
          <p className="account-menu-name">
            {user.displayName || "名前未設定"}
          </p>
          <p className="account-menu-email">
            {user.email || "メールアドレス未設定"}
          </p>
          <button
            className="account-menu-logout"
            type="button"
            onClick={handleLogout}
          >
            ログアウト
          </button>
        </div>
      )}
    </div>
  );
}

export default AccountMenu;
