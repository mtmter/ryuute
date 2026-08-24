let googleMapsLoadPromise = null;

export function loadGoogleMaps() {
  if (window.google?.maps?.importLibrary) {
    return Promise.resolve(window.google.maps);
  }

  if (googleMapsLoadPromise) {
    return googleMapsLoadPromise;
  }

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  if (!apiKey) {
    return Promise.reject(
      new Error("Google Maps APIキーが設定されていません"),
    );
  }

  googleMapsLoadPromise = new Promise((resolve, reject) => {
    const callbackName = "__ryuuteGoogleMapsReady";
    const script = document.createElement("script");
    const query = new URLSearchParams({
      key: apiKey,
      loading: "async",
      libraries: "places",
      callback: callbackName,
      language: "ja",
      region: "JP",
      v: "weekly",
    });

    window[callbackName] = () => {
      delete window[callbackName];
      resolve(window.google.maps);
    };

    script.src = `https://maps.googleapis.com/maps/api/js?${query}`;
    script.async = true;
    script.onerror = () => {
      delete window[callbackName];
      script.remove();
      googleMapsLoadPromise = null;
      reject(new Error("Google Mapsを読み込めませんでした"));
    };
    document.head.append(script);
  });

  return googleMapsLoadPromise;
}
