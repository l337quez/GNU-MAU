print(list(db.aql.execute("FOR doc IN notes_view SEARCH doc.title == 'colocations' RETURN doc.title")))
