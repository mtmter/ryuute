from . import ekispert_provider, mock_provider


ROUTE_PROVIDERS = {
    "mock": mock_provider.get_route,
    "ekispert": ekispert_provider.get_route,
}


def get_route_provider(provider_name):
    """設定名に対応する経路取得関数を返す。"""
    try:
        return ROUTE_PROVIDERS[provider_name]
    except KeyError as error:
        supported_names = ", ".join(ROUTE_PROVIDERS)
        raise ValueError(
            f"ROUTE_PROVIDERは{supported_names}のいずれかを指定してください"
        ) from error
