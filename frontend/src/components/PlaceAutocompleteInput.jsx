import { useEffect, useRef, useState } from "react";
import { loadGoogleMaps } from "../googleMaps";

function PlaceAutocompleteInput({
  id,
  value,
  onChange,
  onPlaceSelect,
  placeholder,
  disabled = false,
  autoFocus = false,
}) {
  const widgetContainerRef = useRef(null);
  const widgetRef = useRef(null);
  const valueRef = useRef(value);
  const disabledRef = useRef(disabled);
  const onChangeRef = useRef(onChange);
  const onPlaceSelectRef = useRef(onPlaceSelect);
  const [status, setStatus] = useState(
    import.meta.env.VITE_GOOGLE_MAPS_API_KEY ? "loading" : "fallback",
  );
  const [errorMessage, setErrorMessage] = useState(
    import.meta.env.VITE_GOOGLE_MAPS_API_KEY
      ? ""
      : "Google Maps APIキーが未設定のため、文字入力で検索します。",
  );

  useEffect(() => {
    valueRef.current = value;
    onChangeRef.current = onChange;
    onPlaceSelectRef.current = onPlaceSelect;

    if (widgetRef.current && widgetRef.current.value !== value) {
      widgetRef.current.value = value;
    }
  }, [onChange, onPlaceSelect, value]);

  useEffect(() => {
    disabledRef.current = disabled;
    if (widgetRef.current) {
      widgetRef.current.disabled = disabled;
    }
  }, [disabled]);

  useEffect(() => {
    if (!import.meta.env.VITE_GOOGLE_MAPS_API_KEY) {
      return undefined;
    }

    let isCancelled = false;
    let autocompleteElement = null;
    let cleanupAutocomplete = null;

    async function setupAutocomplete() {
      try {
        await loadGoogleMaps();
        const { PlaceAutocompleteElement } =
          await window.google.maps.importLibrary("places");

        if (isCancelled) {
          return;
        }

        autocompleteElement = new PlaceAutocompleteElement({
          placeholder,
          requestedLanguage: "ja",
          requestedRegion: "jp",
          value: valueRef.current,
        });
        autocompleteElement.id = id;
        autocompleteElement.className = "place-autocomplete-widget";
        autocompleteElement.disabled = disabledRef.current;

        function handleInput() {
          onPlaceSelectRef.current(null);
          onChangeRef.current(autocompleteElement.value);
        }

        async function handlePlaceSelect(selectEvent) {
          try {
            const place = selectEvent.placePrediction.toPlace();
            await place.fetchFields({
              fields: ["id", "displayName", "formattedAddress", "location"],
            });

            if (isCancelled) {
              return;
            }

            const selectedName =
              place.displayName ||
              place.formattedAddress ||
              autocompleteElement.value;
            autocompleteElement.value = selectedName;
            onChangeRef.current(selectedName);
            onPlaceSelectRef.current({
              name: selectedName,
              address: place.formattedAddress || "",
              place_id: place.id || "",
              lat: place.location?.lat() ?? null,
              lng: place.location?.lng() ?? null,
            });
            setErrorMessage("");
          } catch {
            setErrorMessage(
              "場所の詳細を取得できませんでした。文字入力のまま検索できます。",
            );
          }
        }

        function handlePlacesError() {
          setErrorMessage(
            "場所候補を取得できませんでした。文字入力のまま検索できます。",
          );
        }

        autocompleteElement.addEventListener("input", handleInput);
        autocompleteElement.addEventListener("gmp-select", handlePlaceSelect);
        autocompleteElement.addEventListener("gmp-error", handlePlacesError);
        cleanupAutocomplete = () => {
          autocompleteElement.removeEventListener("input", handleInput);
          autocompleteElement.removeEventListener(
            "gmp-select",
            handlePlaceSelect,
          );
          autocompleteElement.removeEventListener(
            "gmp-error",
            handlePlacesError,
          );
        };

        widgetContainerRef.current.append(autocompleteElement);
        widgetRef.current = autocompleteElement;
        setStatus("ready");

        if (autoFocus) {
          requestAnimationFrame(() => autocompleteElement.focus());
        }
      } catch {
        if (!isCancelled) {
          setStatus("fallback");
          setErrorMessage(
            "場所候補を読み込めませんでした。文字入力のまま検索できます。",
          );
        }
      }
    }

    setupAutocomplete();

    return () => {
      isCancelled = true;
      cleanupAutocomplete?.();
      autocompleteElement?.remove();
      if (widgetRef.current === autocompleteElement) {
        widgetRef.current = null;
      }
    };
  }, [autoFocus, id, placeholder]);

  function handleFallbackChange(inputEvent) {
    onPlaceSelect(null);
    onChange(inputEvent.target.value);
  }

  return (
    <div className="place-autocomplete-container">
      <div
        ref={widgetContainerRef}
        className={status === "ready" ? "" : "is-hidden"}
      />

      {status !== "ready" && (
        <input
          id={id}
          type="text"
          value={value}
          placeholder={placeholder}
          autoFocus={autoFocus}
          disabled={disabled}
          onChange={handleFallbackChange}
        />
      )}

      {status === "loading" && (
        <p className="place-autocomplete-status" role="status">
          場所候補を読み込んでいます
        </p>
      )}

      {errorMessage && (
        <p className="place-autocomplete-error" role="alert">
          {errorMessage}
        </p>
      )}
    </div>
  );
}

export default PlaceAutocompleteInput;
