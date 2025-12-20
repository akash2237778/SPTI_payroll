@echo off
REM Build and Push Docker Images to Docker Hub (Windows)

echo ========================================
echo Building and Pushing SPTI Payroll Images
echo ========================================

REM Configuration
set DOCKER_USERNAME=akash7778
set IMAGE_BACKEND=sptipayroll-backend
set IMAGE_CONSUMER=sptipayroll-consumer
set TAG=0.3

echo.
echo [1/4] Building backend image...
docker build -t %DOCKER_USERNAME%/%IMAGE_BACKEND%:%TAG% .
if errorlevel 1 (
    echo ERROR: Backend build failed!
    exit /b 1
)

echo.
echo [2/4] Tagging consumer image...
docker tag %DOCKER_USERNAME%/%IMAGE_BACKEND%:%TAG% %DOCKER_USERNAME%/%IMAGE_CONSUMER%:%TAG%
if errorlevel 1 (
    echo ERROR: Consumer tag failed!
    exit /b 1
)

echo.
echo [3/4] Pushing backend image...
docker push %DOCKER_USERNAME%/%IMAGE_BACKEND%:%TAG%
if errorlevel 1 (
    echo ERROR: Backend push failed!
    exit /b 1
)

echo.
echo [4/4] Pushing consumer image...
docker push %DOCKER_USERNAME%/%IMAGE_CONSUMER%:%TAG%
if errorlevel 1 (
    echo ERROR: Consumer push failed!
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Images pushed to Docker Hub
echo ========================================
echo.
echo Images:
echo   - %DOCKER_USERNAME%/%IMAGE_BACKEND%:%TAG%
echo   - %DOCKER_USERNAME%/%IMAGE_CONSUMER%:%TAG%
echo.
echo Next steps:
echo   1. Deploy on TrueNAS using docker-compose.truenas-macvlan.yml
echo   2. Verify consumer can reach device (192.168.2.66)
echo   3. Test sync from web interface
echo.
pause
