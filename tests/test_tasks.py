# tests/test_tasks.py
def test_create_and_list_mine(client, owner_headers, create_task):
    t1 = create_task(title="Fix login bug", status="In Progress")
    t2 = create_task(title="Make tea", status="Completed")
    r = client.get("/tasks/mine", headers=owner_headers, params={"page": 1, "limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert any(x["id"] == t1["id"] for x in data["items"])
    assert any(x["id"] == t2["id"] for x in data["items"])
    assert "total_pages" in data

def test_search_and_sort(client, owner_headers, create_task):
    create_task(title="Buy milk", desc="2L milk", status="New")
    create_task(title="Milkshake recipe", desc="almond milk", status="In Progress")

    # search q=milk
    r = client.get("/tasks", headers=owner_headers, params={"q": "milk", "page": 1, "limit": 50})
    assert r.status_code == 200
    items = r.json()["items"]
    assert all("milk" in ((i["title"] + " " + (i.get("description") or "")).lower()) for i in items)

    # sort by title asc
    r = client.get("/tasks", headers=owner_headers,
                   params={"q": "milk", "sort_by": "title", "sort_dir": "asc", "page": 1, "limit": 50})
    items2 = r.json()["items"]
    titles = [i["title"] for i in items2]
    assert titles == sorted(titles)

def test_filter_by_status(client, owner_headers, create_task):
    create_task(title="Task A", status="New")
    create_task(title="Task B", status="Completed")
    r = client.get("/tasks", headers=owner_headers, params={"status": "Completed"})
    assert r.status_code == 200
    assert all(i["status"] == "Completed" for i in r.json()["items"])

def test_complete_owner_only(client, owner_headers, other_headers, create_task):
    t = create_task(title="Owner task", status="New")

    # Not owner -> 403
    r = client.patch(f"/tasks/{t['id']}/complete", headers=other_headers)
    assert r.status_code == 403

    # Owner -> 200 + status Completed
    r = client.patch(f"/tasks/{t['id']}/complete", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "Completed"

def test_update_and_delete_owner_only(client, owner_headers, other_headers, create_task):
    t = create_task(title="To delete", status="New")

    # other user cannot update
    r = client.patch(f"/tasks/{t['id']}", headers=other_headers, json={"title": "Hacked"})
    assert r.status_code == 403

    # other user cannot delete
    r = client.delete(f"/tasks/{t['id']}", headers=other_headers)
    assert r.status_code == 403

    # owner can update
    r = client.patch(f"/tasks/{t['id']}", headers=owner_headers, json={"title": "Updated"})
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"

    # owner can delete
    r = client.delete(f"/tasks/{t['id']}", headers=owner_headers)
    assert r.status_code == 204
