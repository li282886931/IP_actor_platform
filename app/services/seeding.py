from urllib.parse import quote

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from app import database
from app.models import Artist, ProjectVersion, Show, Venue
from app.services.auth import get_or_create_default_context
from app.services.intelligence import seed_market_dossier_data


DEFAULT_ARTISTS = [
    {"name": "周杰伦", "tags": "流行/华语", "heat_score": 95, "fan_count": "5000万", "risk_level": 0, "profile": {}},
    {"name": "五月天", "tags": "摇滚/台湾", "heat_score": 88, "fan_count": "2000万", "risk_level": 0, "profile": {}},
    {"name": "林俊杰", "tags": "流行/R&B", "heat_score": 82, "fan_count": "1500万", "risk_level": 2, "profile": {}},
    {
        "name": "蔡琴",
        "tags": "华语乐坛/丝绒歌后/成熟客群/资深女艺人市场",
        "heat_score": 78,
        "fan_count": "待补充",
        "risk_level": 2,
        "profile": {
            "age": "约68岁",
            "market_positioning": "华语乐坛“丝绒歌后”，纯音乐演唱会",
            "touring_box_office_reference": "2026《不要告别》巡回演唱会全国多城，票价399-1399元，杭州跨年场；宣布2027年底告别歌坛",
            "differentiation_with_zhao_yazhi": "纯歌手路线，无影视IP加持；客群偏成熟（40+）；无“时尚大秀”基因",
            "cooperation_recommendation": "票房稳定；可作“资深女艺人市场”对标；2026年部分场次有取消",
        },
    },
    {
        "name": "毛阿敏",
        "tags": "内地乐坛/大姐大/实力派唱将/拼盘演唱会",
        "heat_score": 70,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约62岁",
            "market_positioning": "内地乐坛大姐大，实力派唱将",
            "touring_box_office_reference": "近年以拼盘演唱会为主，个人巡演较少",
            "differentiation_with_zhao_yazhi": "唱功顶级但综艺曝光少，社交话题度低于赵雅芝",
            "cooperation_recommendation": "适合做嘉宾",
        },
    },
    {
        "name": "刘晓庆",
        "tags": "传奇影后/话剧女王/争议舆情/反面参照",
        "heat_score": 68,
        "fan_count": "待补充",
        "risk_level": 5,
        "profile": {
            "age": "约75岁",
            "market_positioning": "传奇影后+话剧女王，“永不认输”人设",
            "touring_box_office_reference": "话剧《风华绝代》巡演243场（2012-2026），3小时独角戏3万字台词，成都站谢幕跪地引轰动",
            "differentiation_with_zhao_yazhi": "形象争议大：2026年5月开封万岁山商演戴墨镜、躲太阳、被质疑“耍大牌/捞金”，全网负面舆情；75岁仍拍短剧（9天82集），商业感过重",
            "cooperation_recommendation": "与赵雅芝“优雅松弛”路线反差极大；品牌安全性低，不建议合作，仅作反面参照",
        },
    },
    {
        "name": "林青霞",
        "tags": "华语影坛传奇/东方不败/稀缺公开活动",
        "heat_score": 86,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约71岁",
            "market_positioning": "华语影坛传奇，东方不败",
            "touring_box_office_reference": "极少公开活动，无个人演唱会/大秀计划",
            "differentiation_with_zhao_yazhi": "国民度顶级但已半隐退，商业化可能性极低",
            "cooperation_recommendation": "仅作对标参考，不可替代",
        },
    },
    {
        "name": "汪明荃",
        "tags": "港圈大姐大/TVB/粤语区/怀旧市场",
        "heat_score": 76,
        "fan_count": "待补充",
        "risk_level": 3,
        "profile": {
            "age": "约78岁",
            "market_positioning": "港圈大姐大，TVB活化石",
            "touring_box_office_reference": "近年有演唱会，680元档开票十分钟抢光，VIP三天售完；观众含白发老人+年轻人举灯牌",
            "differentiation_with_zhao_yazhi": "粤语区影响力大，内地号召力弱于赵雅芝；走路需人扶，体力受限",
            "cooperation_recommendation": "地域局限明显，仅粤语区对标",
        },
    },
    {
        "name": "蔡国庆",
        "tags": "内地军旅歌手/祝福歌曲/拼盘演出/嘉宾",
        "heat_score": 63,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约57岁",
            "market_positioning": "内地军旅歌手，“一年有三百六十五个祝福”",
            "touring_box_office_reference": "拼盘演出为主",
            "differentiation_with_zhao_yazhi": "男艺人，客群偏中老年男性，与18-40岁女性定位不符",
            "cooperation_recommendation": "适合做嘉宾",
        },
    },
    {
        "name": "陈慧娴",
        "tags": "港乐天后/千千阙歌/粤港澳/怀旧市场",
        "heat_score": 74,
        "fan_count": "待补充",
        "risk_level": 1,
        "profile": {
            "age": "约65岁",
            "market_positioning": "港乐天后，《千千阙歌》",
            "touring_box_office_reference": "近年巡演，粤港澳号召力强",
            "differentiation_with_zhao_yazhi": "纯歌手路线，时尚属性弱",
            "cooperation_recommendation": "粤语区为主，可对标港乐怀旧市场",
        },
    },
    {
        "name": "潘迎紫",
        "tags": "一代女皇/冻龄女神/内地首秀/同台嘉宾",
        "heat_score": 72,
        "fan_count": "待补充",
        "risk_level": 2,
        "profile": {
            "age": "约76岁",
            "market_positioning": "“一代女皇”，冻龄女神鼻祖",
            "touring_box_office_reference": "2026年4月成都“走进原声带”内地首秀",
            "differentiation_with_zhao_yazhi": "与赵雅芝同属“冻龄”赛道，但影视IP以武则天为主，内地活动极少",
            "cooperation_recommendation": "可作为对打/同台嘉宾",
        },
    },
    {
        "name": "费玉清类",
        "tags": "已封麦/不可用/对标排除",
        "heat_score": 0,
        "fan_count": "不适用",
        "risk_level": 0,
        "profile": {
            "age": "—",
            "market_positioning": "已封麦",
            "touring_box_office_reference": "2019年已正式封麦退出演艺圈",
            "differentiation_with_zhao_yazhi": "不可用",
            "cooperation_recommendation": "—",
        },
    },
]


def build_show_poster_url(title: str, artist_name: str = '', city: str = '', venue: str = ''):
    prompt = quote(
        (
            f"Realistic live concert photography for {artist_name or title}, "
            f"{title}, {city or 'major city'} {venue or 'concert venue'}, "
            "wide stage, audience, professional lighting, premium editorial event poster, no text"
        )
    )
    return f"https://copilot-cn.bytedance.net/api/ide/v1/text_to_image?prompt={prompt}&image_size=landscape_4_3"


def seed_initial_data(db: Session):
    artists_by_name = {artist.name: artist for artist in db.query(Artist).all()}
    for item in DEFAULT_ARTISTS:
        artist = artists_by_name.get(item["name"])
        if not artist:
            artist = Artist(name=item["name"])
            db.add(artist)
        artist.tags = item["tags"]
        artist.heat_score = item["heat_score"]
        artist.fan_count = item["fan_count"]
        artist.risk_level = item["risk_level"]
        artist.profile = item["profile"]
    db.commit()

    if db.query(Show).count() == 0:
        artists_by_name = {artist.name: artist for artist in db.query(Artist).all()}
        a1 = artists_by_name['周杰伦']
        a2 = artists_by_name['五月天']
        a3 = artists_by_name['林俊杰']
        s1 = Show(title='周杰伦·北京演唱会', artist_id=a1.id, artist_name=a1.name, city='北京', date='2026-09-10', venue='鸟巢', price='380-1280', status='on_sale', description='周杰伦个人巡回演唱会 — 北京站')
        s2 = Show(title='五月天·上海演唱会', artist_id=a2.id, artist_name=a2.name, city='上海', date='2026-12-31', venue='梅赛德斯-奔驰文化中心', price='480-1280', status='on_sale', description='五月天跨年演唱会 — 上海站')
        s3 = Show(title='林俊杰小巨蛋特别场', artist_id=a3.id, artist_name=a3.name, city='台北', date='2026-10-05', venue='台北小巨蛋', price='420-980', status='on_sale', description='林俊杰抒情特别场')
        for show in [s1, s2, s3]:
            show.poster_url = build_show_poster_url(show.title, show.artist_name, show.city, show.venue)
        db.add_all([s1, s2, s3])
        db.commit()

    seeded_titles = {'周杰伦·北京演唱会', '五月天·上海演唱会', '林俊杰小巨蛋特别场'}
    for show in db.query(Show).filter(Show.title.in_(seeded_titles)).all():
        if not show.poster_url:
            show.poster_url = build_show_poster_url(show.title, show.artist_name, show.city, show.venue)
    db.commit()

    seed_market_dossier_data(db)
    seed_venue_reference_data(db)


def seed_venue_reference_data(db: Session):
    tenant, _ = get_or_create_default_context(db)
    existing_keys = {
        (venue.city, venue.name)
        for venue in db.query(Venue).filter(Venue.tenant_id == tenant.id).all()
    }
    for show in db.query(Show).all():
        city = (show.city or '').strip()
        name = (show.venue or '').strip()
        if not city or not name or name == '待定' or (city, name) in existing_keys:
            continue
        db.add(Venue(
            tenant_id=tenant.id,
            city=city,
            name=name,
            source=f"show:{show.id}",
        ))
        existing_keys.add((city, name))
    db.commit()


def ensure_runtime_columns():
    inspector = inspect(database.engine)
    if not inspector.has_table('users'):
        return

    user_columns = {column['name'] for column in inspector.get_columns('users')}
    statements = []
    if 'artist_id' not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN artist_id INTEGER")
    if 'password_hash' not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN password_hash VARCHAR(128) DEFAULT ''")
    if 'group_code' not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN group_code VARCHAR(64) DEFAULT 'B'")

    if inspector.has_table('artists'):
        artist_columns = {column['name'] for column in inspector.get_columns('artists')}
        if 'profile' not in artist_columns:
            statements.append("ALTER TABLE artists ADD COLUMN profile JSON")

    if inspector.has_table('tasks'):
        task_columns = {column['name'] for column in inspector.get_columns('tasks')}
        if 'evidence_ids' not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN evidence_ids JSON")
        if 'rejection_reason' not in task_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN rejection_reason TEXT")

    if inspector.has_table('shows'):
        show_columns = {column['name'] for column in inspector.get_columns('shows')}
        if 'poster_url' not in show_columns:
            statements.append("ALTER TABLE shows ADD COLUMN poster_url TEXT")

    if inspector.has_table('ai_generations'):
        generation_columns = {column['name'] for column in inspector.get_columns('ai_generations')}
        for column_name in ('tenant_id', 'user_id'):
            if column_name not in generation_columns:
                statements.append(f"ALTER TABLE ai_generations ADD COLUMN {column_name} INTEGER")

    if inspector.has_table('projects'):
        project_columns = {column['name'] for column in inspector.get_columns('projects')}
        project_column_definitions = {
            'artist_id': 'INTEGER',
            'venue_id': 'INTEGER',
            'source_project_id': 'INTEGER',
            'available_funds': 'INTEGER',
            'venue_capacity': 'INTEGER',
            'ticket_tiers': 'JSON',
            'conservative_occupancy_rate': 'INTEGER',
            'neutral_occupancy_rate': 'INTEGER',
            'optimistic_occupancy_rate': 'INTEGER',
        }
        for column_name, column_type in project_column_definitions.items():
            if column_name not in project_columns:
                statements.append(
                    f"ALTER TABLE projects ADD COLUMN {column_name} {column_type}"
                )

    if not statements:
        return

    with database.engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def init_db():
    database.Base.metadata.create_all(bind=database.engine)
    ensure_runtime_columns()
    db = database.SessionLocal()
    try:
        seed_initial_data(db)
        get_or_create_default_context(db)
    finally:
        db.close()


def next_project_version_no(db: Session, project_id: int):
    return (db.query(func.max(ProjectVersion.version_no)).filter(ProjectVersion.project_id == project_id).scalar() or 0) + 1
