import { formatTime } from "../dateUtils";

function getTransportLabel(type) {
  if (type === "WALK") {
    return "徒歩";
  }

  if (type === "TRANSIT") {
    return "公共交通";
  }

  return type;
}

function RouteSearchResult({
  errorMessage,
  isRegistering,
  onRegister,
  onRetry,
  route,
}) {
  return (
    <div className="route-result">
      <div className="route-result-heading">
        <h3>経路検索結果</h3>
        <div className="route-result-times" aria-label="経路全体の所要時間">
          <div>
            <strong>{formatTime(route.departure_at)}</strong>
            <span>出発</span>
          </div>
          <p>{route.duration_minutes}分</p>
          <div>
            <strong>{formatTime(route.arrival_at)}</strong>
            <span>到着</span>
          </div>
        </div>
      </div>

      <div className="route-timeline">
        <div className="route-place route-origin">
          <span aria-hidden="true" />
          <strong>{route.origin}</strong>
        </div>

        {route.segments.map((segment, index) => (
          <div
            className="route-segment-group"
            key={`${segment.departure_at}-${index}`}
          >
            <div className="route-segment">
              <span className="route-segment-line" aria-hidden="true" />
              <div className="route-segment-details">
                <strong>
                  {segment.type === "TRANSIT" && segment.line_name
                    ? segment.line_name
                    : getTransportLabel(segment.type)}
                </strong>
                <span>
                  {getTransportLabel(segment.type)}・{segment.duration_minutes}分
                </span>
                <span>
                  {segment.from} → {segment.to}
                </span>
                <span>
                  {formatTime(segment.departure_at)} →{" "}
                  {formatTime(segment.arrival_at)}
                </span>
              </div>
            </div>

            <div className="route-place">
              <span aria-hidden="true" />
              <strong>{segment.to}</strong>
            </div>
          </div>
        ))}

        <p className="route-destination-label">目的地：{route.destination}</p>
      </div>

      {errorMessage && (
        <p className="modal-error-message" role="alert">
          {errorMessage}
        </p>
      )}

      <div className="modal-actions route-result-actions">
        <button
          className="secondary-button"
          type="button"
          disabled={isRegistering}
          onClick={onRetry}
        >
          検索条件を変更
        </button>
        <button
          className="primary-button"
          type="button"
          disabled={isRegistering}
          onClick={() => onRegister?.(route)}
        >
          {isRegistering ? "保存中..." : "この経路を登録"}
        </button>
      </div>
    </div>
  );
}

export default RouteSearchResult;
