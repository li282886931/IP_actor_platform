"""Public metadata for built-in connector capabilities."""


def _definition(
    key,
    name,
    source_kind,
    domain,
    availability,
    *,
    auth_type='vendor_contract',
    adapter_key='',
    fields=None,
    capabilities=None,
    description='',
):
    return {
        "key": key,
        "name": name,
        "source_kind": source_kind,
        "domain": domain,
        "description": description or f"{name}的只读数据能力。",
        "auth_type": auth_type,
        "config_schema": {"fields": fields or []},
        "capabilities": capabilities or ["read"],
        "adapter_key": adapter_key,
        "availability": availability,
        "human_verification_required": True,
        "version": 1,
    }


_ENDPOINT_FIELDS = [
    {"name": "endpoint", "type": "url", "required": True},
    {"name": "read_only", "type": "boolean", "required": True, "default": True},
]
_MCP_FIELDS = [
    *_ENDPOINT_FIELDS,
    {"name": "tool", "type": "text", "required": True},
    {"name": "url_argument", "type": "text", "required": True, "default": "url"},
]

BUILTIN_CONNECTORS = [
    _definition("agent_api", "通用只读 API", "api", "general", "available",
                auth_type="bearer", adapter_key="agent_api", fields=_ENDPOINT_FIELDS),
    _definition("mcp_web", "只读网页 MCP", "mcp", "general", "available",
                auth_type="bearer", adapter_key="mcp_web", fields=_MCP_FIELDS),
    _definition("organizer_files", "主办方资料", "file", "general", "available",
                auth_type="none", adapter_key="organizer_files"),
    _definition("spreadsheet_evidence", "表格证据导入", "file", "general", "available",
                auth_type="none", adapter_key="spreadsheet_evidence"),
    _definition("custom_rest_api", "自定义只读 REST API", "api", "general", "available",
                auth_type="bearer", adapter_key="custom_rest_api", fields=_ENDPOINT_FIELDS),
    _definition("custom_mcp", "自定义只读 MCP", "mcp", "general", "available",
                auth_type="bearer", adapter_key="custom_mcp", fields=_MCP_FIELDS),
    _definition("custom_skill", "自定义 Skill", "skill", "general", "runner_required",
                auth_type="none", adapter_key="custom_skill"),
    _definition("amap", "高德场馆", "api", "venue", "available", auth_type="api_key",
                adapter_key="amap", capabilities=["search", "read"], fields=[{
                    "name": "operation", "type": "select", "required": True,
                    "options": ["venue_search"], "default": "venue_search",
                }]),
    _definition("baidu_maps", "百度地图", "api", "venue", "adapter_required"),
    _definition("tencent_lbs", "腾讯位置服务", "api", "venue", "adapter_required"),
    _definition("venue_official_api", "场馆官方接口", "api", "venue", "contract_required"),
    _definition("city_culture_tourism_api", "城市文旅接口", "api", "city", "contract_required"),
    _definition("city_transport_api", "城市交通接口", "api", "city", "contract_required"),
    _definition("hotel_market_api", "酒店市场接口", "api", "city", "contract_required"),
    _definition("qweather", "和风天气", "api", "weather", "available", auth_type="api_key",
                adapter_key="qweather", fields=[{
                    "name": "operation", "type": "select", "required": True,
                    "options": ["daily_forecast"], "default": "daily_forecast",
                }]),
    _definition("qweather_warning", "和风天气预警", "api", "weather", "adapter_required"),
    _definition("cma_weather", "官方气象数据", "api", "weather", "contract_required"),
    _definition("venue_iot", "场馆现场传感器", "api", "weather", "contract_required"),
    _definition("artist_agency_api", "艺人经纪接口", "api", "artist", "contract_required"),
    _definition("weibo_open", "微博开放平台", "api", "artist", "contract_required"),
    _definition("douyin_open", "抖音开放平台", "api", "artist", "contract_required"),
    _definition("xiaohongshu_business", "小红书企业数据", "api", "artist", "contract_required"),
    _definition("bilibili_open", "B站开放平台", "api", "artist", "contract_required"),
    _definition("wechat_index", "微信指数", "api", "artist", "contract_required"),
    _definition("baidu_index", "百度指数", "api", "artist", "contract_required"),
    _definition("qq_music_business", "QQ音乐业务数据", "api", "artist", "contract_required"),
    _definition("netease_music_business", "网易云音乐业务数据", "api", "artist", "contract_required"),
    _definition("kugou_kuwo_business", "酷狗酷我业务数据", "api", "artist", "contract_required"),
    _definition("sentiment_mcp", "合规舆情 MCP", "mcp", "artist", "adapter_required"),
    _definition("ticketing_api", "主办方票务接口", "api", "ticketing", "adapter_required"),
    _definition("damai_business", "大麦授权销售数据", "api", "ticketing", "contract_required"),
    _definition("maoyan_business", "猫眼授权销售数据", "api", "ticketing", "contract_required"),
    _definition("showstart_business", "秀动授权销售数据", "api", "ticketing", "contract_required"),
    _definition("ticket_refund_api", "退票退款状态", "api", "ticketing", "contract_required"),
    _definition("ticket_entry_api", "实名核销入场数据", "api", "ticketing", "contract_required"),
    _definition("audience_crm", "观众 CRM", "api", "ticketing", "contract_required"),
    _definition("brand_crm", "品牌 CRM", "api", "brand", "contract_required"),
    _definition("sponsor_rights_api", "赞助权益核验", "api", "brand", "adapter_required"),
    _definition("ad_exposure_api", "广告曝光数据", "api", "brand", "contract_required"),
    _definition("commerce_sales_api", "电商销售归因", "api", "brand", "contract_required"),
    _definition("finance_erp", "财务 ERP", "api", "finance", "contract_required"),
    _definition("invoice_api", "发票税务资料", "api", "finance", "contract_required"),
    _definition("payment_settlement_api", "支付结算状态", "api", "finance", "contract_required"),
    _definition("bank_supervision_api", "监管账户状态", "api", "finance", "contract_required"),
    _definition("government_approval_api", "项目报批状态", "api", "compliance", "contract_required"),
    _definition("public_security_api", "公安审批备案", "api", "compliance", "contract_required"),
    _definition("fire_safety_api", "消防材料检查", "api", "compliance", "contract_required"),
    _definition("copyright_registry_api", "版权授权登记", "api", "compliance", "contract_required"),
    _definition("esign_contract_api", "电子合同状态", "api", "compliance", "contract_required"),
    _definition("entry_flow_api", "现场客流状态", "api", "operations", "contract_required"),
    _definition("security_incident_api", "安保事件记录", "api", "operations", "contract_required"),
]

for _key, _name in [
    ("market_research_skill", "市场资料归纳"),
    ("ip_research_skill", "IP 对标研究"),
    ("audience_profile_skill", "粉丝画像归纳"),
    ("city_analysis_skill", "城市市场分析"),
    ("content_strategy_skill", "宣发内容策略"),
    ("hook_analyzer_skill", "视频钩子分析"),
    ("risk_classification_skill", "风险目录归类"),
    ("case_retrieval_skill", "历史案例检索"),
    ("report_synthesis_skill", "报告综合"),
    ("review_calibration_skill", "复盘校准"),
]:
    BUILTIN_CONNECTORS.append(
        _definition(
            _key,
            _name,
            "skill",
            "skill",
            "runner_required",
            auth_type="none",
            adapter_key=_key,
        )
    )

BUILTIN_SKILL_KEYS = frozenset(
    item["key"] for item in BUILTIN_CONNECTORS if item["source_kind"] == "skill"
)
