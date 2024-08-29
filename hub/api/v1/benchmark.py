from os import getenv
from typing import List, Optional

import boto3
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.models import Benchmark, BenchmarkResult, get_session

load_dotenv()
S3_BUCKET = getenv("S3_BUCKET")

s3 = boto3.client("s3")

v1_router = APIRouter(
    prefix="/benchmark",
    tags=["benchmark"],
)


def requires_login(auth: AuthToken = Depends(revokable_auth)):
    return auth.account_id


@v1_router.get("/create")
async def create_benchmark(
    namespace: str = Depends(requires_login),
    benchmark_name: str = Form(...),
    solver_name: str = Form(...),
    solver_kwargs: str = Form(...),
) -> int:
    with get_session() as session:
        benchmark = Benchmark(
            namespace=namespace,
            benchmark_name=benchmark_name,
            solver_name=solver_name,
            solver_kwargs=solver_kwargs,
        )
        session.add(benchmark)
        session.commit()
    return benchmark.id


@v1_router.get("/get")
async def get_benchmark(
    namespace: str,
    benchmark_name: str,
    solver_name: str,
    solver_kwargs: str,
) -> Optional[int]:
    with get_session() as session:
        query = select(Benchmark).where(
            namespace == namespace,
            benchmark_name == benchmark_name,
            solver_name == solver_name,
            solver_kwargs == solver_kwargs,
        )
        benchmark = session.exec(query).first()

        if benchmark is None:
            return None
        else:
            return benchmark.id


@v1_router.get("/list")
async def list_benchmarks(
    namespace: Optional[str] = None,
    benchmark_name: Optional[str] = None,
    solver_name: Optional[str] = None,
    solver_args: Optional[str] = None,
    total: int = 32,
    offset: int = 0,
) -> List[Benchmark]:
    query = select(Benchmark)
    if namespace is not None:
        query.where(Benchmark.namespace == namespace)
    if benchmark_name is not None:
        query.where(Benchmark.benchmark == benchmark_name)
    if solver_name is not None:
        query.where(Benchmark.solver == solver_name)
    if solver_args is not None:
        query.where(Benchmark.args == solver_args)

    query = query.offset(offset).limit(total)

    with get_session() as session:
        benchmarks = session.exec(query).all()
        return benchmarks


@v1_router.get("/add_result")
async def add_benchmark_result(
    namespace: str = Depends(requires_login),
    benchmark_id: int = Form(...),
    index: int = Form(...),
    solved: bool = Form(...),
    info: str = Form(...),
):
    with get_session() as session:
        benchmark_q = select(Benchmark).where(Benchmark.id == benchmark_id)
        benchmark = session.exec(benchmark_q).first()

        if benchmark is None:
            raise HTTPException(status_code=404, detail=f"Benchmark {benchmark_id} not found")

        if benchmark.namespace != namespace:
            raise HTTPException(status_code=403, detail="Not authorized to add result")

        result_q = select(BenchmarkResult).where(
            BenchmarkResult.benchmark_id == benchmark_id,
            BenchmarkResult.index == index,
        )
        result = session.exec(result_q).first()

        if result is not None:
            raise HTTPException(status_code=409, detail=f"Result {index} already exists")

        result = BenchmarkResult(
            benchmark_id=benchmark_id,
            index=index,
            solved=solved,
            info=info,
        )
        session.add(result)
        session.commit()


class BenchmarkResultOutput(BaseModel):
    index: int
    solved: bool
    info: str


@v1_router.get("/get_result")
async def get_benchmark_result(benchmark_id: int) -> List[BenchmarkResultOutput]:
    query = select(BenchmarkResult).where(BenchmarkResult.benchmark_id == benchmark_id)
    with get_session() as session:
        results = session.exec(query).all()
        return [
            BenchmarkResultOutput(
                index=result.index,
                solved=result.solved,
                info=result.info,
            )
            for result in results
        ]
