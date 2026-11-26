print('Test 5:'); print(list(db.aql.execute("FOR doc IN Notes RETURN {title: doc.title, pid: doc.project_id}")))
