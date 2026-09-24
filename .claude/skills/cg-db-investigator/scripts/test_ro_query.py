import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location("ro", pathlib.Path(__file__).with_name("ro-query.py"))
ro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ro)

ALLOWED = [
    'db.getMongo().getDBNames()',
    'db.getSiblingDB("cases").getCollectionNames()',
    'db.getCollection("users").find({ updatedAt: { $gt: ISODate("2026-01-01") }, isDeleted: false }).sort({ createdAt: -1 }).limit(5).toArray()',
    'db.getCollection("policies").aggregate([{ $match: { status: "active" } }, { $group: { _id: "$tenantId", n: { $sum: 1 } } }]).toArray()',
    'const r = db.getCollection("x").find({ _id: ObjectId("65a1b2c3d4e5f6a7b8c9d0e1") }).toArray(); printjson(r[0])',
    'db.getCollection("x").find({}).toArray().map(d => d.updatedAt)',
]

REJECTED = [
    'db.getCollection("users").deleteMany({})',
    'db.users.updateOne({ _id: 1 }, { $set: { a: 1 } })',
    'db.getCollection("x").insertOne({ a: 1 })',
    'db.getCollection("x").drop()',
    'db.dropDatabase()',
    'db.getCollection("x").aggregate([{ $out: "y" }])',
    'db.getCollection("x").aggregate([{ $merge: { into: "y" } }])',
    'db.runCommand({ delete: "x", deletes: [] })',
    'db.adminCommand({ shutdown: 1 })',
    'db.getCollection("x").findOneAndUpdate({}, { $set: { a: 1 } })',
    'db.getCollection("x")["dele" + "teMany"]({})',
    'const k = "deleteMan" + "y"; db.getCollection("x")[k]({})',
    'const find = db.getCollection("x")[k]; find({})',
    'const { [k]: find } = db.getCollection("x"); find({})',
    'db.getCollection("x").\\u0064eleteMany({})',
    'load("evil.js")',
    'eval("db.x.drop()")',
    'db.getCollection("x").find({ $where: "sleep(1000)" })',
    'use admin',
]


def test_guard():
    for q in ALLOWED:
        assert not ro.violations(q), (q, ro.violations(q))
    for q in REJECTED:
        assert ro.violations(q), q


if __name__ == "__main__":
    test_guard()
    print("ok")
