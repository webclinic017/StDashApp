import streamlit as st

try:
    from pynse import *
    import datetime
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    import plotly.express as px


except ModuleNotFoundError as e:
    st.error(
        f"Looks like requirements are not installed: '{e}'. Run the following command to install requirements"
    )

    st.code(
        "pip install streamlit matplotlib mplfinance plotly git+https://github.com/StreamAlpha/pynse.git"
    )
else:
    nse = Nse()

    def bhavcopy_display():

        with st.sidebar:
            st.write("Bhavcopy Inputs")
            req_date = st.date_input("Select Date", datetime.date.today())
            segment = st.selectbox("Select Segment", ["Cash", "FnO"])

        req_date = None if req_date >= datetime.date.today() else req_date

        if segment == "Cash":
            bhavcopy = nse.bhavcopy(req_date)
        else:
            bhavcopy = nse.bhavcopy_fno(req_date)

        st.write(f"{segment} bhavcopy for {req_date}")

        st.download_button(
            "Download", bhavcopy.to_csv(), file_name=f"{segment}_bhav_{req_date}.csv"
        )
        st.write(bhavcopy)

    def stock_deliv_data():

        with st.sidebar:
            symbol = st.selectbox("Select Symbol", nse.symbols[IndexSymbol.All.name])

            from_date = st.date_input(
                "From date", datetime.date.today() - datetime.timedelta(30)
            )

            to_date = st.date_input("To Date", datetime.date.today())

        trading_days = nse.get_hist(from_date=from_date, to_date=to_date).index
        trading_days = list(trading_days.map(lambda x: x.date()))
        data = pd.DataFrame()

        for date in trading_days:
            try:
                bhav = nse.bhavcopy(date).loc[symbol]
                bhav.set_index("DATE1", inplace=True)
                data = data.append(bhav)
            except Exception as e:
                print(f"error {e} for {date}")

        data = data.astype(float)
        data.index = data.index.map(pd.to_datetime)
        data = data[
            [
                "OPEN_PRICE",
                "HIGH_PRICE",
                "LOW_PRICE",
                "CLOSE_PRICE",
                "TTL_TRD_QNTY",
                "DELIV_QTY",
                "DELIV_PER",
            ]
        ]

        data.columns = "open high low close volume deliv_qty deliv_per".split()

        deliv_data = [mpf.make_addplot(data["deliv_per"], panel=2, ylabel="deliv %")]
        fig, ax = mpf.plot(
            data,
            addplot=deliv_data,
            type="candle",
            style="yahoo",
            volume=True,
            returnfig=True,
            title=f"{symbol} Delivery %",
            figratio=(16, 7),
            figscale=1.2,
        )

        st.write(fig)

        st.write(data)

    def high_low_deliv():
        with st.sidebar:
            req_date = st.date_input("Select Date", datetime.date.today())
            sort_by = st.radio("Sort By", ["Hightest", "Lowest"])

            index_name = st.selectbox("Index", [i.name for i in IndexSymbol])
            no_of_stocks = st.number_input("No of Stocks", value=10, step=1)

        req_date = None if req_date >= datetime.date.today() else req_date

        bhavcopy = nse.bhavcopy(req_date)

        bhavcopy = bhavcopy.reset_index(level=1)

        bhavcopy = bhavcopy[
            [
                "OPEN_PRICE",
                "HIGH_PRICE",
                "LOW_PRICE",
                "CLOSE_PRICE",
                "TTL_TRD_QNTY",
                "DELIV_QTY",
                "DELIV_PER",
            ]
        ]
        bhavcopy = bhavcopy.sort_values(
            "DELIV_PER", ascending=True if sort_by == "Lowest" else False
        )

        bhavcopy = bhavcopy[bhavcopy.index.isin(nse.symbols[index_name])]

        st.write(bhavcopy.head(int(no_of_stocks)))

    def stock_oi_data():
        with st.sidebar:
            symbol = st.selectbox("Symbol", nse.symbols[IndexSymbol.FnO.name])
            from_date = st.date_input(
                "From Date", datetime.date.today() - datetime.timedelta(days=30)
            )
            to_date = st.date_input("To Date", datetime.date.today())

        if to_date < from_date or to_date > datetime.date.today():
            st.error("check from date and to date")

        else:

            trading_days = nse.get_hist(from_date=from_date, to_date=to_date).index
            trading_days = list(trading_days.map(lambda x: x.date()))
            data = pd.DataFrame()

            for date in trading_days:
                try:
                    bhav = nse.bhavcopy_fno(date).loc[symbol]
                    bhav = bhav[bhav["INSTRUMENT"].isin(["FUTSTK", "FUTIDX"])]
                    expiry_list = list(bhav["EXPIRY_DT"].sort_values())
                    current_expiry = expiry_list[0]

                    coi = bhav["OPEN_INT"].sum()

                    ccoi = bhav["CHG_IN_OI"].sum()

                    bhav["DATE"] = bhav["TIMESTAMP"].apply(
                        lambda x: datetime.datetime.strptime(x, "%d-%b-%Y").date()
                    )
                    bhav = bhav[bhav["EXPIRY_DT"] == current_expiry]

                    bhav["OPEN_INT"] = coi
                    bhav["CHG_IN_OI"] = ccoi

                    bhav.set_index("DATE", inplace=True)
                    data = data.append(bhav)
                except Exception as e:
                    print(f"error {e} for {date}")

            data = data[
                [
                    "EXPIRY_DT",
                    "OPEN",
                    "HIGH",
                    "LOW",
                    "CLOSE",
                    "CONTRACTS",
                    "OPEN_INT",
                    "CHG_IN_OI",
                ]
            ]

            data.columns = [col.lower() for col in data.columns]
            data.index = data.index.map(pd.to_datetime)

            oi_plots = [mpf.make_addplot(data["open_int"], panel=1, ylabel="coi")]
            fig, ax = mpf.plot(
                data,
                addplot=oi_plots,
                type="candle",
                style="yahoo",
                returnfig=True,
                figratio=(16, 7),
                figscale=1.2,
                title=f"{symbol} Cumulative OI",
            )

            st.write(fig)

            st.write(data)

    def future_builtup():
        with st.sidebar:

            from_date = st.date_input(
                "From Date", datetime.date.today() - datetime.timedelta(days=1)
            )
            to_date = st.date_input("To Date", datetime.date.today())

        if to_date < from_date or to_date > datetime.date.today():
            st.error("check from date and to date")

        else:
            bhav_1 = nse.bhavcopy_fno(to_date)
            bhav_2 = nse.bhavcopy_fno(from_date)
            bhav_1 = bhav_1[(bhav_1.INSTRUMENT.isin(["FUTSTK", "FUTIDX"]))]
            bhav_2 = bhav_2[(bhav_2.INSTRUMENT.isin(["FUTSTK", "FUTIDX"]))]

            group_bhav_1 = bhav_1.groupby(bhav_1.index)
            group_bhav_2 = bhav_2.groupby(bhav_2.index)

            current_expiry_1 = group_bhav_1.EXPIRY_DT.min()
            current_expiry_2 = group_bhav_2.EXPIRY_DT.min()

            bhav_1["current_expiry"] = current_expiry_1
            bhav_2["current_expiry"] = current_expiry_2

            bhav_1 = bhav_1[bhav_1.EXPIRY_DT == bhav_1.current_expiry]
            bhav_2 = bhav_2[bhav_2.EXPIRY_DT == bhav_2.current_expiry]

            pch_oi = group_bhav_1["OPEN_INT"].sum() / group_bhav_2["OPEN_INT"].sum() - 1
            pch_close = bhav_1.CLOSE / bhav_2.CLOSE - 1

            builtup = pd.DataFrame({"pch_close": pch_close, "pch_oi": pch_oi})
            builtup = builtup.reset_index()

            fig = px.scatter(
                builtup,
                "pch_close",
                "pch_oi",
                hover_data=["SYMBOL"],
                width=1280,
                height=420,
            )
            fig.add_hline(y=0.0)
            fig.add_vline(x=0.0)

            st.write(fig)
            cols = st.columns([1, 1])
            with cols[0]:
                st.write("## Long Builtup")

                lb = (
                    builtup[(builtup.pch_close > 0) & (builtup.pch_oi > 0)]
                    .sort_values(by="pch_close", ascending=False)
                    .head()
                )
                st.write(lb)

            with cols[1]:
                st.write("## Short Builtup")

                sb = (
                    builtup[(builtup.pch_close < 0) & (builtup.pch_oi > 0)]
                    .sort_values(by="pch_close", ascending=True)
                    .head()
                )
                st.write(sb)

            cols = st.columns([1, 1])

            with cols[0]:
                st.write("## Long Unwinding")

                lu = (
                    builtup[(builtup.pch_close < 0) & (builtup.pch_oi < 0)]
                    .sort_values(by="pch_close", ascending=True)
                    .head()
                )
                st.write(lu)

            with cols[1]:
                st.write("## Short Covering")

                sc = (
                    builtup[(builtup.pch_close > 0) & (builtup.pch_oi < 0)]
                    .sort_values(by="pch_close", ascending=True)
                    .head()
                )
                st.write(sc)

    def bhavcopy_to_option_chain(symbol, date, expiry_date=None):

        expiry_date = expiry_date or get_expiry_dates(symbol, date)[0]

        bhavcopy = nse.bhavcopy_fno(date)

        # subset bhavcopy for options data
        options_data = bhavcopy[(bhavcopy.INSTRUMENT.isin(["OPTSTK", "OPTIDX"]))]

        # find all the expiry dates for symbols
        options_grouped = options_data.groupby(options_data.index)

        options_data = options_data.loc[symbol]

        options_data = options_data[
            options_data.EXPIRY_DT == pd.to_datetime(expiry_date)
        ]

        options_data.set_index(options_data.STRIKE_PR, inplace=True)
        # remove the undesired columns
        options_data = options_data[
            [
                "STRIKE_PR",
                "OPTION_TYP",
                "OPEN",
                "HIGH",
                "LOW",
                "CLOSE",
                "CONTRACTS",
                "OPEN_INT",
                "CHG_IN_OI",
            ]
        ]

        # seperate call and put details
        call_data = options_data[options_data.OPTION_TYP == "CE"]
        put_data = options_data[options_data.OPTION_TYP == "PE"]

        # get the futures price
        futures_data = bhavcopy[bhavcopy.INSTRUMENT.isin(["FUTSTK", "FUTIDX"])].loc[
            symbol
        ]

        futures_price = (
            futures_data[futures_data.EXPIRY_DT == futures_data.EXPIRY_DT.min()]
            .iloc[0]
            .CLOSE
        )

        atm_strike = abs(options_data.STRIKE_PR - futures_price).idxmin()

        return call_data, put_data, futures_price, atm_strike

    def get_expiry_dates(symbol, req_date):
        bhavcopy = nse.bhavcopy_fno(req_date)

        # subset bhavcopy for options data
        options_data = bhavcopy[(bhavcopy.INSTRUMENT.isin(["OPTSTK", "OPTIDX"]))].loc[
            symbol
        ]
        expiry_dates = sorted(list(set(options_data.EXPIRY_DT)), reverse=False)
        return expiry_dates

    def historical_option_chain():
        with st.sidebar:
            symbol = st.selectbox("Symbol", nse.symbols[IndexSymbol.FnO.name])
            req_date = st.date_input("Date", value=datetime.date.today())

            expiry_list = get_expiry_dates(symbol, req_date)
            expiry_list = [d.date() for d in expiry_list]

            expiry_date = st.selectbox("Expiry Date", expiry_list)

        call_data, put_data, futures_price, atm_strike = bhavcopy_to_option_chain(
            symbol, req_date, expiry_date
        )

        call_data = call_data[
            [
                # "STRIKE_PR",
                "OPTION_TYP",
                "CLOSE",
                "CONTRACTS",
                "OPEN_INT",
                "CHG_IN_OI",
            ]
        ]
        put_data = put_data[
            [
                # "STRIKE_PR",
                "OPTION_TYP",
                "CLOSE",
                "CONTRACTS",
                "OPEN_INT",
                "CHG_IN_OI",
            ]
        ]

        option_chain = pd.concat([call_data, put_data], keys=["CALL", "PUT"], axis=1)

        st.download_button(
            "Download",
            option_chain.to_csv(),
            file_name=f"option_chain_{symbol}_{req_date}_exp_{expiry_date}.csv",
        )
        st.table(option_chain)

    def put_call_ratio():
        with st.sidebar:
            symbol = st.selectbox("Symbol", nse.symbols[IndexSymbol.FnO.name])
            from_date = st.date_input(
                "From Date", datetime.date.today() - datetime.timedelta(days=30)
            )
            to_date = st.date_input("To Date", datetime.date.today())

        if to_date < from_date or to_date > datetime.date.today():
            st.error("check from date and to date")
        else:
            trading_days = nse.get_hist(from_date=from_date, to_date=to_date).index
            trading_days = list(trading_days.map(lambda x: x.date()))

            pcr_data = pd.DataFrame()

            for date in trading_days:
                try:
                    bhav = nse.bhavcopy_fno(date).loc[symbol]
                    bhav = bhav[bhav.INSTRUMENT.isin(["FUTSTK", "FUTIDX"])]
                    expiry_list = list(bhav["EXPIRY_DT"].sort_values())
                    current_expiry = expiry_list[0]

                    bhav["DATE"] = bhav.TIMESTAMP.apply(
                        lambda x: datetime.datetime.strptime(x, "%d-%b-%Y").date()
                    )
                    bhav = bhav[bhav.EXPIRY_DT == current_expiry]

                    bhav.set_index("DATE", inplace=True)  # = bhav.DATE1

                    option_chain_data = bhavcopy_to_option_chain(symbol, date)
                    pcr = (
                        option_chain_data[1].OPEN_INT.sum()
                        / option_chain_data[0].OPEN_INT.sum()
                    )

                    bhav["pcr"] = pcr

                    pcr_data = pcr_data.append(bhav)

                except Exception as e:
                    print(f"error for {date}")

            pcr_data.index = pcr_data.index.map(pd.to_datetime)
            pcr_data.columns = [c.lower() for c in pcr_data.columns]

            pcr_plot = [mpf.make_addplot(pcr_data.pcr, panel=1, ylabel="PCR")]

            fig, ax = mpf.plot(
                pcr_data,
                addplot=pcr_plot,
                returnfig=True,
                type="candle",
                style="yahoo",
                figratio=(16, 7),
                figscale=1.2,
                title=f"{symbol} PCR",
            )

            st.write(fig)

            st.table(pcr_data)

    def point_loss(call_data, put_data, strike):
        itm_calls = call_data[call_data["STRIKE_PR"] < strike]
        itm_puts = put_data[put_data["STRIKE_PR"] > strike]

        call_loss = (strike - itm_calls["STRIKE_PR"]) * itm_calls["OPEN_INT"]
        put_loss = (itm_puts["STRIKE_PR"] - strike) * itm_puts["OPEN_INT"]

        return call_loss.sum() + put_loss.sum()

    def max_pain():
        with st.sidebar:
            symbol = st.selectbox("Symbol", nse.symbols[IndexSymbol.FnO.name])
            req_date = st.date_input("From Date", datetime.date.today())
            expiry_list = get_expiry_dates(symbol, req_date)
            expiry_list = [d.date() for d in expiry_list]

            expiry_date = st.selectbox("Expiry Date", expiry_list)

        call_data, put_data, futures_price, atm_strike = bhavcopy_to_option_chain(
            symbol, req_date, expiry_date
        )

        loss = call_data["STRIKE_PR"].apply(
            lambda x: point_loss(call_data, put_data, x)
        )

        max_pain = loss.idxmin()

        ax = loss.plot(figsize=(8, 5), title=f"{symbol} max Pain")
        plt.axvline(x=max_pain)
        plt.text(max_pain, 0, f"Max Pain = {max_pain}", rotation=90)

        st.write(ax.get_figure())

    analysis_dict = {
        "Bhavcopy": bhavcopy_display,
        "Stock Delivery Data": stock_deliv_data,
        "High/Low Delivery": high_low_deliv,
        "Stock OI Data": stock_oi_data,
        "Future Builtup": future_builtup,
        "Historical Option Chain": historical_option_chain,
        "Put Call Ratio": put_call_ratio,
        "Max Pain": max_pain,
    }

    with st.sidebar:
        selected_analysis = st.radio("Select Analysis", list(analysis_dict.keys()))
        st.write("---")

    st.header(selected_analysis)

    analysis_dict[selected_analysis]()
