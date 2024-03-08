import pandas as pd
import numpy as np
import streamlit as st
import altair as alt
from altair import limit_rows, to_values
import toolz
import sqlite3


def t(data):
    return toolz.curried.pipe(data, limit_rows(max_rows=300000), to_values)


alt.data_transformers.register("custom", t)
alt.data_transformers.enable("custom")

conn = sqlite3.connect("./data.db")


@st.experimental_memo(max_entries=10)
def get_mst():
    conn = sqlite3.connect("./data.db")
    region_list = pd.read_sql("SELECT region FROM region", conn)["region"]
    pref_list = pd.read_sql("SELECT pref FROM prefecture", conn)["pref"]
    sql = """
    SELECT
        hpcd
        ,hpname
        ,region
        ,pref
        ,med2
        ,city
        ,bed
    FROM hp
    LEFT JOIN prefecture ON hp.pref_id = prefecture.pref_id
    LEFT JOIN region ON prefecture.region_id = region.region_id;
    """
    hp = pd.read_sql(sql, conn)
    hp_list = hp["hpname"]
    mdcname_list = pd.read_sql("SELECT mdcname FROM mdc2_mst", conn)["mdcname"]
    mdc6name_list = pd.read_sql("SELECT DISTINCT mdc6name FROM mdc26_mst", conn)[
        "mdc6name"
    ]
    conn.close()
    return region_list, pref_list, hp, hp_list, mdcname_list, mdc6name_list


@st.experimental_memo(max_entries=10, ttl=3600)
def pref(hp, select_prefs):
    hp = hp.loc[hp["pref"].isin(select_prefs)]
    return hp


@st.experimental_memo(max_entries=10, ttl=3600)
def med2(hp, select_med2s):
    hp = hp.loc[hp["med2"].isin(select_med2s)]
    return hp


@st.experimental_memo(max_entries=10, ttl=3600)
def city(hp, select_citys):
    hp = hp.loc[hp["city"].isin(select_citys)]
    return hp


@st.experimental_memo(max_entries=10, ttl=3600)
def filter_region(hp, select_region):
    return hp.loc[hp["region"] == select_region]


def set_location(hp, pref_list):
    hp_list = hp["hpname"].unique()
    select_hpname = st.sidebar.multiselect("医療機関名", hp_list)
    init_pref = []
    init_med2 = []
    if select_hpname != []:
        tmp = hp.loc[hp["hpname"].isin(select_hpname)]
        init_pref = tmp["pref"].unique()
        init_med2 = tmp["med2"].unique()
    ###############################################################
    try:
        select_prefs = st.sidebar.multiselect(
            "都道府県", pref_list, default=list(init_pref)
        )
        if select_prefs != []:
            hp = pref(hp, select_prefs)
            init_med2 = hp.loc[hp["hpname"].isin(select_hpname)]["med2"].unique()
        else:
            init_med2 = []

    except:
        select_prefs = st.sidebar.multiselect("都道府県", pref_list)
        if select_prefs != []:
            hp = pref(hp, select_prefs)
            init_med2 = hp.loc[hp["hpname"].isin(select_hpname)]["med2"].unique()
        else:
            init_med2 = []
    #############################################################
    try:
        if len(select_prefs) == 1:
            select_med2s = st.sidebar.multiselect(
                "二次医療圏", list(hp["med2"].unique()), default=list(init_med2)
            )
        else:
            select_med2s = st.sidebar.multiselect(
                "二次医療圏", list(hp["med2"].unique())
            )
        if select_med2s != []:
            hp = med2(hp, select_med2s)

    except:
        select_med2s = st.sidebar.multiselect("二次医療圏", list(hp["med2"].unique()))
        if select_med2s != []:
            hp = med2(hp, select_med2s)

    ############################################################
    select_citys = st.sidebar.multiselect("市区町村", list(hp["city"].unique()))
    if select_citys != []:
        hp = city(hp, select_citys)

    return select_prefs, select_med2s, select_citys, select_hpname, hp


@st.experimental_memo(max_entries=10, ttl=3600)
def get_select_hpcd(hp, select_hpname, set_min, set_max):
    hp = hp.loc[hp["bed"].between(set_min, set_max)]
    selecthpnames = set(hp["hpname"]).union(select_hpname)
    select_hpcd = hp.loc[hp["hpname"].isin(selecthpnames)]["hpcd"]
    return select_hpcd


@st.experimental_memo(max_entries=10, ttl=3600)
def get_value_data(select_hpcd, select_hpname, hp_list, mdcname_list, mdc6name_list):
    conn = sqlite3.connect("./data.db")
    # mdc2dの取得
    sql = f"""
    SELECT
        hpname
        ,mdcname
        ,value
    FROM mdc2d
    INNER JOIN hp 
        ON mdc2d.hpcd = hp.hpcd
        AND hp.hpcd in {tuple(select_hpcd)}
    INNER JOIN mdc2_mst ON mdc2d.mdc2 = mdc2_mst.mdc2
    """
    mdc2d = pd.read_sql(sql, conn)
    mdc2d["hpname"] = pd.Categorical(mdc2d["hpname"], categories=hp_list)
    mdc2d["mdcname"] = pd.Categorical(mdc2d["mdcname"], categories=mdcname_list)
    # mdc6dの取得
    sql = f"""
    SELECT
        hpname
        ,mdcname
        ,mdc6name
        ,value
    FROM mdc6d
    INNER JOIN hp 
        ON mdc6d.hpcd = hp.hpcd
        AND hp.hpcd in {tuple(select_hpcd)}
    INNER JOIN mdc26_mst ON mdc6d.mdc6 = mdc26_mst.mdc6
    INNER JOIN mdc2_mst ON mdc26_mst.mdc2 = mdc2_mst.mdc2
    ;
    """
    mdc6d = pd.read_sql(sql, conn)
    mdc6d["hpname"] = pd.Categorical(mdc6d["hpname"], categories=hp_list)
    mdc6d["mdcname"] = pd.Categorical(mdc6d["mdcname"], categories=mdcname_list)
    mdc6d["mdc6name"] = pd.Categorical(mdc6d["mdc6name"], categories=mdc6name_list)
    # opedの取得
    sql = f"""
    WITH mdc_mst as  (
        SELECT
            mdc2_mst.mdc2
            ,mdc2_mst.mdcname
            ,mdc26_mst.mdc6
            ,mdc26_mst.mdc6name
        FROM mdc2_mst
        INNER JOIN mdc26_mst ON mdc2_mst.mdc2 = mdc26_mst.mdc2
    )
    SELECT
        oped.hpcd
        ,hp.hpname
        ,mdc_mst.mdcname
        ,oped.mdc6
        ,mdc_mst.mdc6name
        ,oped.ope
        ,ope_mst.opename
        ,oped.value
        ,hp.bed
    FROM oped
    INNER JOIN hp 
        ON oped.hpcd = hp.hpcd
        AND hp.hpcd in {tuple(select_hpcd)}
    INNER JOIN mdc_mst ON oped.mdc6 = mdc_mst.mdc6
    INNER JOIN ope_mst ON oped.mdc6 = ope_mst.mdc6 and oped.ope = ope_mst.ope;
    
    """
    oped = pd.read_sql(sql, conn)
    oped["hpname"] = pd.Categorical(oped["hpname"], categories=hp_list)
    oped["mdcname"] = pd.Categorical(oped["mdcname"], categories=mdcname_list)
    oped["mdc6name"] = pd.Categorical(oped["mdc6name"], categories=mdc6name_list)
    oped["hp"] = " "
    conn.close()

    # 散布図のshape用の処理
    if select_hpname != []:
        oped["hp"] = oped["hp"].mask(oped["hpname"].isin(select_hpname), oped["hpname"])

    return mdc2d, mdc6d, oped


@st.experimental_memo(max_entries=10, ttl=3600)
def draw_chart(select_hpname, mdc2d, mdc6d, oped):
    ##################################################################
    top_hight = 370
    top_width = 490
    second_hight = 370
    second_width = 190
    color_scheme = "category20b"
    #########################################################
    # 医療機関名が選択されたらその病院を赤くする。
    # vegaが標準ではラベルのテキスト変更に対応していないので、文字列で指定
    # '(datum.value ==  "北里大学病院")|(datum.value ==  "九州大学病院")'
    if select_hpname == []:
        label_color = "black"
    else:
        to_colors = []
        for hpname in select_hpname:
            to_colors.append(f'(datum.value == "{hpname}")')
        color_condition = "|".join(to_colors)
        label_color = alt.condition(
            color_condition, alt.value("#E80000"), alt.value("black")
        )
    #######################################################
    # 共通で使用するセレクターの設定
    mdc_selection = alt.selection_multi(fields=["mdcname"], empty="all")
    mdc_color = alt.condition(
        mdc_selection,
        alt.Color(
            "mdcname:N",
            title="MDC2",
            # legend=None,
            scale=alt.Scale(scheme=color_scheme),
        ),
        alt.value("lightgray"),
    )

    mdc6_selection = alt.selection_single(fields=["mdc6name"], empty="all")
    mdc6_color = alt.condition(
        mdc6_selection,
        alt.Color("mdcname:N", title="MDC2", scale=alt.Scale(scheme=color_scheme)),
        alt.value("lightgray"),
    )
    ope_selection = alt.selection_single(fields=["opename"], empty="all")
    ope_color = alt.condition(
        ope_selection,
        alt.Color("mdcname:N", title="MDC2", scale=alt.Scale(scheme=color_scheme)),
        alt.value("lightgray"),
    )
    ######################################################################
    oped_base1 = (
        alt.Chart(oped).transform_filter(mdc_selection).transform_filter(mdc6_selection)
    )
    oped_base2 = oped_base1.transform_filter(ope_selection)
    #######################################################################
    oped_base3 = (
        oped_base2.transform_joinaggregate(hp_value="sum(value)", groupby=["hpname"])
        .transform_window(
            hp_rank="dense_rank()",
            sort=[{"field": "hp_value", "order": "descending"}],
        )
        .transform_filter((alt.datum.hp_rank < 20) & (alt.datum.value > 0))
    )

    hp_bars = oped_base3.encode(
        x=alt.X("sum(value)", title="件数"),
        y=alt.Y("hpname", sort="-x", title=None, axis=alt.Axis(labelColor=label_color)),
        color=mdc_color,
        tooltip=[
            alt.Tooltip("hpname", title="病院名"),
            alt.Tooltip("bed:Q", title="病床数", format=","),
            alt.Tooltip("mdcname", title="MDC2"),
            alt.Tooltip("sum(value)", title="件数", format=","),
        ],
    ).properties(width=top_width, height=top_hight, title="病院別・疾患別実績")

    hp_text = oped_base3.encode(
        x=alt.X("sum(value)", title=None),
        y=alt.Y("hpname", sort="-x", title=None),
        text=alt.Text("sum(value)", format=","),
    )

    hp_bars = hp_bars.mark_bar() + hp_text.mark_text(
        align="left", baseline="middle", dx=3
    ).add_selection(mdc_selection)
    ###################################################################
    # hp_point = oped_base2.transform_aggregate(
    #     sum_value='sum(value)',
    #     groupby=['hpname', 'bed', 'mdcname', 'hp']
    hp_point = (
        oped_base2.mark_point()
        .encode(
            x=alt.X("sum(value):Q", title="件数"),
            y=alt.Y("bed:Q", title="病床数", scale=alt.Scale(zero=False)),
            color=mdc_color,
            shape=alt.Shape("hp", title="shape"),
            size=alt.Size("sum(value):Q", title="size"),
            tooltip=[
                alt.Tooltip("hpname", title="病院名"),
                alt.Tooltip("bed:Q", title="病床数", format=","),
                alt.Tooltip("sum(value):Q", title="件数", format=","),
            ],
        )
        .properties(width=top_width, height=top_hight, title="病床数別・疾患別実績")
        .add_selection(mdc_selection)
    )

    ###################################################################
    mdc_bars = (
        alt.Chart(mdc2d)
        .encode(
            x=alt.X("sum(value):Q", title=None),
            y=alt.Y("mdcname", sort="-x", title=None),
            color=mdc_color,
            tooltip=[
                alt.Tooltip("mdcname", title="MDC2"),
                alt.Tooltip("sum(value):Q", title="件数", format=","),
            ],
        )
        .properties(
            width=second_width,
            height=second_hight,
            title={
                "text": ["指定地域内患者数　　　　　　　　　MDC2別"],
                "fontSize": 14,
                "anchor": "start",
            },
        )
    )
    mdc_text = alt.Chart(mdc2d).encode(
        x=alt.X("sum(value)", title=None),
        y=alt.Y("mdcname", sort="-x", title=None),
        text=alt.Text("sum(value)", format=","),
    )

    mdc_bars = mdc_bars.mark_bar() + mdc_text.mark_text(
        align="left", baseline="middle", dx=3
    ).add_selection(mdc_selection)

    ###################################################################
    # mdc6_base = alt.Chart(mdc6d).transform_filter(
    #     mdc_selection
    # ).transform_joinaggregate(
    #     mdc6_value='sum(value):Q',
    #     groupby=['mdcname', 'mdc6name']
    # ).transform_window(
    #     mdc6_rank='dense_rank(mdc6_value:Q)',
    #     sort=[alt.SortField('mdc6_value', order='descending')]
    # ).transform_filter(
    #     alt.datum.mdc6_rank < 20
    # )

    mdc6_base = (
        alt.Chart(mdc6d)
        .transform_filter(mdc_selection)
        .transform_joinaggregate(
            mdc6_value="sum(value):Q", groupby=["mdcname", "mdc6name"]
        )
        .transform_filter(
            (
                (alt.datum.mdc6name != "010000 差分")
                & (alt.datum.mdc6name != "020000 差分")
                & (alt.datum.mdc6name != "030000 差分")
                & (alt.datum.mdc6name != "040000 差分")
                & (alt.datum.mdc6name != "050000 差分")
                & (alt.datum.mdc6name != "060000 差分")
                & (alt.datum.mdc6name != "070000 差分")
                & (alt.datum.mdc6name != "080000 差分")
                & (alt.datum.mdc6name != "090000 差分")
                & (alt.datum.mdc6name != "100000 差分")
                & (alt.datum.mdc6name != "110000 差分")
                & (alt.datum.mdc6name != "120000 差分")
                & (alt.datum.mdc6name != "130000 差分")
                & (alt.datum.mdc6name != "140000 差分")
                & (alt.datum.mdc6name != "150000 差分")
                & (alt.datum.mdc6name != "160000 差分")
                & (alt.datum.mdc6name != "170000 差分")
                & (alt.datum.mdc6name != "180000 差分")
            )
        )
        .transform_window(
            mdc6_rank="dense_rank(mdc6_value:Q)",
            sort=[alt.SortField("mdc6_value", order="descending")],
        )
        .transform_filter(alt.datum.mdc6_rank < 20)
    )
    mdc6_bars = mdc6_base.encode(
        x=alt.X("sum(value):Q", title=None),
        y=alt.Y("mdc6name", sort="-x", title=None),
        color=mdc6_color,
        tooltip=[
            alt.Tooltip("mdc6name", title="MDC6"),
            alt.Tooltip("sum(value):Q", title="件数", format=","),
        ],
    ).properties(width=second_width, height=second_hight, title="MDC6別")
    mdc6_text = mdc6_base.encode(
        x=alt.X("sum(value):Q", title=None),
        y=alt.Y("mdc6name", sort="-x", title=None),
        text=alt.Text("sum(value):Q", format=","),
    )
    mdc6_bars = mdc6_bars.mark_bar() + mdc6_text.mark_text(
        align="left", baseline="middle", dx=3
    ).add_selection(mdc6_selection)
    ###################################################################
    ope_base4 = (
        oped_base1.transform_joinaggregate(
            ope_value="sum(value):Q", groupby=["mdcname", "mdc6name", "opename"]
        )
        .transform_filter((alt.datum.opename != "0 差分"))
        .transform_window(
            ope_rank="dense_rank(ope_value:Q)",
            sort=[alt.SortField("ope_value", order="descending")],
        )
        .transform_filter(alt.datum.ope_rank < 20)
    )
    ope_bars = ope_base4.encode(
        x=alt.X("sum(value):Q", title=None),
        y=alt.Y("opename", sort="-x", title=None),
        color=ope_color,
        tooltip=[
            alt.Tooltip("mdcname", title="MDC2"),
            alt.Tooltip("mdc6name", title="MDC6"),
            alt.Tooltip("opename", title="手術"),
            alt.Tooltip("sum(value):Q", title="件数", format=","),
        ],
    ).properties(width=second_width, height=second_hight, title="手術別")
    ope_text = ope_base4.encode(
        x=alt.X("sum(value):Q", title=None),
        y=alt.Y("opename", sort="-x", title=None),
        text=alt.Text("sum(value):Q", format=","),
    )
    ope_bars = ope_bars.mark_bar() + ope_text.mark_text(
        align="left", baseline="middle", dx=3
    ).add_selection(ope_selection)
    ###################################################################
    # chartの結合　select_hpnameがなければこのchartsを返す
    top_chart = alt.hconcat(hp_bars, hp_point)
    second_chart = alt.hconcat(mdc_bars, mdc6_bars, ope_bars)
    ###################################################################
    # select_hpがあった場合は1病院ずつchartを作成して、chartsの下側に追加する。
    if select_hpname != []:
        # 2病院以上選択して件数を比較することを想定し最大値で尺度を合わせる
        mdc2_max = np.max(mdc2d.loc[mdc2d["hpname"].isin(select_hpname), "value"])
        mdc6_max = np.max(mdc6d.loc[mdc6d["hpname"].isin(select_hpname)]["value"])
        ope_max = np.max(oped.loc[oped["hpname"].isin(select_hpname)]["value"])
        ###############################################################
        for hpname in select_hpname:
            # 病院ごとに集計　0件削除
            hp_mdc2 = mdc2d.loc[mdc2d["hpname"] == hpname]
            hp_mdc2 = hp_mdc2.loc[hp_mdc2["value"] > 0]
            hp_mdc6 = mdc6d.loc[mdc6d["hpname"] == hpname]
            hp_mdc6 = hp_mdc6.loc[hp_mdc6["value"] > 0]
            hp_ope = oped.loc[oped["hpname"] == hpname]
            hp_ope = hp_ope.loc[hp_ope["value"] > 0]
            ####################################################
            hp_mdc2_bars = (
                alt.Chart(hp_mdc2)
                .mark_bar()
                .encode(
                    x=alt.X("value", title=None, scale={"domain": [0, mdc2_max]}),
                    y=alt.Y("mdcname", sort="-x", title=None),
                    color=mdc_color,
                    tooltip=[
                        alt.Tooltip("mdcname", title="MDC2"),
                        alt.Tooltip("value:Q", title="件数", format=","),
                    ],
                )
                .properties(
                    width=second_width,
                    height=second_hight,
                    title={
                        "text": [f"{hpname}"],
                        "limit": 300,
                        "fontSize": 12,
                        "anchor": "start",
                    },
                )
            )
            hp_mdc2_text = alt.Chart(hp_mdc2).encode(
                x=alt.X("value", title=None),
                y=alt.Y("mdcname", sort="-x", title=None),
                text=alt.Text("value", format=","),
            )
            hp_mdc2_bars = hp_mdc2_bars.mark_bar() + hp_mdc2_text.mark_text(
                align="left", baseline="middle", dx=3
            ).add_selection(mdc_selection)
            ####################################################
            hp_mdc6_base = (
                alt.Chart(hp_mdc6)
                .transform_filter(mdc_selection)
                .transform_filter(
                    (
                        (alt.datum.mdc6name != "010000 差分")
                        & (alt.datum.mdc6name != "020000 差分")
                        & (alt.datum.mdc6name != "030000 差分")
                        & (alt.datum.mdc6name != "040000 差分")
                        & (alt.datum.mdc6name != "050000 差分")
                        & (alt.datum.mdc6name != "060000 差分")
                        & (alt.datum.mdc6name != "070000 差分")
                        & (alt.datum.mdc6name != "080000 差分")
                        & (alt.datum.mdc6name != "090000 差分")
                        & (alt.datum.mdc6name != "100000 差分")
                        & (alt.datum.mdc6name != "110000 差分")
                        & (alt.datum.mdc6name != "120000 差分")
                        & (alt.datum.mdc6name != "130000 差分")
                        & (alt.datum.mdc6name != "140000 差分")
                        & (alt.datum.mdc6name != "150000 差分")
                        & (alt.datum.mdc6name != "160000 差分")
                        & (alt.datum.mdc6name != "170000 差分")
                        & (alt.datum.mdc6name != "180000 差分")
                    )
                )
                .transform_window(
                    sort=[alt.SortField("value", order="descending")],
                    rank="rank(row_number)",
                )
                .transform_filter(alt.datum.rank < 20)
            )
            hp_mdc6_bars = hp_mdc6_base.encode(
                x=alt.X("sum(value)", title=None, scale={"domain": [0, mdc6_max]}),
                y=alt.Y("mdc6name", sort="-x", title=None),
                color=mdc6_color,
                tooltip=[
                    alt.Tooltip("mdc6name", title="MDC6"),
                    alt.Tooltip("sum(value):Q", title="件数", format=","),
                ],
            ).properties(
                width=second_width,
                height=second_hight,
            )
            hp_mdc6_text = hp_mdc6_base.encode(
                x=alt.X("sum(value)", title=None, scale={"domain": [0, mdc6_max]}),
                y=alt.Y("mdc6name", sort="-x", title=None),
                text=alt.Text("sum(value)", format=","),
            )
            hp_mdc6_bars = hp_mdc6_bars.mark_bar() + hp_mdc6_text.mark_text(
                align="left", baseline="middle", dx=3
            ).add_selection(mdc6_selection)
            ###################################################
            hp_ope_base = (
                alt.Chart(hp_ope)
                .transform_filter(mdc_selection)
                .transform_filter(mdc6_selection)
                .transform_filter((alt.datum.opename != "0 差分"))
                .transform_window(
                    rank="rank(row_number)",
                    sort=[alt.SortField("value", order="descending")],
                )
                .transform_filter(alt.datum.rank < 20)
            )
            hp_ope_bars = hp_ope_base.encode(
                x=alt.X("sum(value):Q", title=None, scale={"domain": [0, ope_max]}),
                y=alt.Y("opename", sort="-x", title=None),
                color=ope_color,
                tooltip=[
                    alt.Tooltip("mdcname", title="MDC2"),
                    alt.Tooltip("mdc6name", title="MDC6"),
                    alt.Tooltip("opename", title="手術"),
                    alt.Tooltip("sum(value):Q", title="件数", format=","),
                ],
            ).properties(width=second_width, height=second_hight)
            hp_ope_text = hp_ope_base.encode(
                x=alt.X("sum(value):Q", title=None, scale={"domain": [0, ope_max]}),
                y=alt.Y("opename", sort="-x", title=None),
                text=alt.Text("sum(value):Q", format=","),
            )
            hp_ope_bars = hp_ope_bars.mark_bar() + hp_ope_text.mark_text(
                align="left", baseline="middle", dx=3
            ).add_selection(ope_selection)
            ####################################################
            hp_charts = alt.hconcat(hp_mdc2_bars | hp_mdc6_bars | hp_ope_bars)
            top_chart = alt.vconcat(top_chart, hp_charts)
            #####################################################
    charts = alt.vconcat(top_chart, second_chart)
    charts = charts.configure_title(
        fontSize=14,
        anchor="middle",
    )
    charts.properties(width="container")
    return charts
