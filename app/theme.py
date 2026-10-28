"""RailPulse theme: colour tokens + Plotly template."""

COLOR_TOKENS = {
    "bg_page": "#F2F6FE",
    "surface": "#FFFFFF",
    "blob": "#D9E6FF",
    "blob_soft": "#ECF2FF",
    "periwinkle": "#B6C4F8",
    "indigo": "#6E7FE6",
    "navy": "#33325C",
    "accent": "#FB7B1B",
    "accent_hover": "#E86A0C",
    "text_strong": "#2B2B33",
    "text": "#55565E",
    "text_muted": "#8A8B94",
    "success": "#2EAD7A",
    "danger": "#E5484D",
}

CHART_PALETTE = ["#6E7FE6", "#33325C", "#B6C4F8", "#FB7B1B", "#8FA8F5", "#C9D3F7"]


def get_plotly_template():
    import plotly.graph_objects as go

    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#55565E"),
        title=dict(font=dict(family="Montserrat, sans-serif", size=18, color="#2B2B33")),
        xaxis=dict(
            gridcolor="#EEF2FB",
            zeroline=False,
            tickfont=dict(color="#8A8B94"),
            title=dict(font=dict(color="#8A8B94")),
        ),
        yaxis=dict(
            gridcolor="#EEF2FB",
            zeroline=False,
            tickfont=dict(color="#8A8B94"),
            title=dict(font=dict(color="#8A8B94")),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="#FFFFFF", font=dict(color="#33325C")),
        colorway=CHART_PALETTE,
    )
    return template


RAILPULSE_TEMPLATE = get_plotly_template()


def apply_theme(fig):
    fig.update_layout(template=RAILPULSE_TEMPLATE)
    return fig
