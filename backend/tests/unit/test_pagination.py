from app.utils.pagination import PageParams, paginate_dict, project_fields


def test_page_params_skip_and_fields():
    params = PageParams(page=3, page_size=10, fields="id,title,company")
    assert params.skip == 20
    assert params.field_list() == ["id", "title", "company"]


def test_paginate_and_project():
    docs = [{"id": "1", "title": "A", "extra": "x"}, {"id": "2", "title": "B", "extra": "y"}]
    projected = project_fields(docs, ["id", "title"])
    assert projected[0] == {"id": "1", "title": "A"}
    page = paginate_dict(projected, total=2, page=1, page_size=10)
    assert page["pages"] == 1
    assert len(page["items"]) == 2
